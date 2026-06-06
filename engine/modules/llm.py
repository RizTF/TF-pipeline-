"""
Provider-agnostic LLM layer.

One entry point — `complete()` — that the rest of the engine calls instead of
talking to a vendor SDK directly. Each *task* (classify, reply, objection,
draft, brief, research) is routed through an ordered chain of
``(provider, model)`` candidates and fails over automatically: if the primary
provider errors, times out, or is rate limited, the next candidate serves the
request.

This gives us three things:

  * cost control  — route bulk/cheap tasks to cheaper models or providers
  * resilience    — automatic backup if the Anthropic API is down
  * zero lock-in  — swap models/providers via .env, no code changes

Performance is unchanged on the happy path: a successful primary call is a
single request with no added latency or extra round-trips. Failover only
triggers on an actual error, and a per-call timeout means a hung provider
fails fast to the backup rather than blocking the pipeline.

Supported providers
-------------------
  * ``anthropic`` — native Anthropic SDK (primary).
  * ``openai``    — OpenAI SDK. Set ``OPENAI_BASE_URL`` to point the same
                    adapter at *any* OpenAI-compatible API — OpenRouter, Groq,
                    DeepSeek, Together, Google's OpenAI-compatible endpoint, or
                    a local Ollama / LM Studio server. One adapter, dozens of
                    cheap or backup models.

Routing
-------
Defaults keep every task on the primary Claude model (so behaviour and quality
are identical to today) and add OpenAI as an automatic backup *only* if
``OPENAI_API_KEY`` is set. Override any task with an env var, e.g.::

    LLM_ROUTE_CLASSIFY="anthropic:claude-haiku-4-5-20251001, openai:gpt-4o-mini"
    LLM_ROUTE_REPLY="anthropic:claude-sonnet-4-6, openai:gpt-4o"
    LLM_ROUTE_DEFAULT="anthropic:claude-sonnet-4-6, openai:gpt-4o"

Format is a comma-separated list of ``provider:model`` candidates, tried
left to right. A candidate is skipped if its provider has no API key, so the
same .env works whether or not a backup is configured.
"""

import json
import logging
import os
import re
import time

from config.settings import (
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    LLM_MODEL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
)

logger = logging.getLogger("tf.llm")


class LLMError(RuntimeError):
    """Raised when every provider in a task's routing chain has failed."""


# ── Default routing chain ────────────────────────────────────────────
# Anthropic primary; OpenAI appended as automatic backup only if a key exists.
_DEFAULT_CHAIN = [("anthropic", LLM_MODEL)]
if OPENAI_API_KEY:
    _DEFAULT_CHAIN.append(("openai", OPENAI_MODEL))


# ── Lazily-initialised SDK clients ───────────────────────────────────
_anthropic_client = None
_openai_client = None


def _anthropic_call(model, system, user, max_tokens, temperature, json_mode, timeout):
    """Native Anthropic call. `system` is a top-level arg, not a message."""
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic

        _anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature

    resp = _anthropic_client.with_options(timeout=timeout).messages.create(**kwargs)
    return resp.content[0].text.strip()


def _openai_call(model, system, user, max_tokens, temperature, json_mode, timeout):
    """
    OpenAI-compatible call. Works against OpenAI or any compatible endpoint
    via OPENAI_BASE_URL. `system` becomes a system-role message.
    """
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        kw = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kw["base_url"] = OPENAI_BASE_URL
        _openai_client = OpenAI(**kw)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "timeout": timeout,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = _openai_client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


_PROVIDERS = {
    "anthropic": _anthropic_call,
    "openai": _openai_call,
}


def _provider_available(provider: str) -> bool:
    if provider == "anthropic":
        return bool(ANTHROPIC_API_KEY)
    if provider == "openai":
        return bool(OPENAI_API_KEY)
    return False


def _is_transient(exc: Exception) -> bool:
    """
    Heuristic: should we retry the *same* provider, or fail straight over to
    the next one? Network/rate/overload errors are worth a quick retry; auth
    and bad-request errors are not.
    """
    blob = f"{exc.__class__.__name__} {exc}".lower()
    transient_markers = (
        "timeout", "timed out", "rate", "overloaded", "connection",
        "unavailable", "temporar", "429", "500", "502", "503", "529",
    )
    return any(m in blob for m in transient_markers)


def _backoff(attempt: int) -> float:
    return min(0.5 * (2 ** attempt), 8.0)


def _parse_chain(spec: str):
    chain = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            provider, model = part.split(":", 1)
        else:
            provider, model = "anthropic", part
        chain.append((provider.strip(), model.strip()))
    return chain


def _chain_for(task: str):
    """Resolve the routing chain for a task, dropping unconfigured providers."""
    spec = os.getenv(f"LLM_ROUTE_{task.upper()}", "").strip() or os.getenv(
        "LLM_ROUTE_DEFAULT", ""
    ).strip()
    chain = _parse_chain(spec) if spec else list(_DEFAULT_CHAIN)

    available = [(p, m) for (p, m) in chain if _provider_available(p)]
    if not available:
        # Last resort: primary Anthropic model, so a misconfigured route never
        # leaves a task with nowhere to go.
        available = [("anthropic", LLM_MODEL)]
    return available


def complete(
    *,
    user: str,
    system: str = "",
    task: str = "default",
    max_tokens: int = 800,
    temperature=None,
    json_mode: bool = False,
) -> str:
    """
    Run a completion for `task`, failing over across the routing chain.

    Returns the model's text response. Raises `LLMError` only if *every*
    candidate provider fails.
    """
    chain = _chain_for(task)
    attempts = 1 + max(0, LLM_MAX_RETRIES)
    last_exc = None

    for idx, (provider, model) in enumerate(chain):
        call = _PROVIDERS.get(provider)
        if call is None:
            logger.warning("Unknown LLM provider '%s' for task '%s' — skipping", provider, task)
            continue

        for attempt in range(attempts):
            try:
                text = call(model, system, user, max_tokens, temperature, json_mode, LLM_TIMEOUT)
                if idx > 0 or attempt > 0:
                    logger.info(
                        "LLM task '%s' served by %s:%s (failover idx=%d, attempt=%d)",
                        task, provider, model, idx, attempt,
                    )
                return text
            except Exception as e:  # noqa: BLE001 — provider SDKs raise many types
                last_exc = e
                transient = _is_transient(e)
                logger.warning(
                    "LLM %s:%s failed for task '%s' (attempt %d/%d, transient=%s): %s",
                    provider, model, task, attempt + 1, attempts, transient, e,
                )
                if transient and attempt < attempts - 1:
                    time.sleep(_backoff(attempt))
                    continue
                break  # non-transient or out of retries → next candidate

    raise LLMError(f"All LLM candidates failed for task '{task}': {last_exc}") from last_exc


def extract_json(text: str) -> dict:
    """
    Parse a JSON object from a model response, tolerating markdown code fences
    and surrounding prose. Raises json.JSONDecodeError if nothing parses.
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    t = t.strip()

    try:
        return json.loads(t)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", t, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def active_providers():
    """Return the list of providers that currently have credentials configured."""
    return [p for p in _PROVIDERS if _provider_available(p)]
