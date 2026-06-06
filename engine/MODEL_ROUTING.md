# Model Routing & Failover

The engine no longer talks to the Anthropic SDK directly. Every AI call goes
through a single provider-agnostic layer — `modules/llm.py` — so you can switch
models or providers to **save money** and have an **automatic backup if the
Claude API is down**, without changing any code or affecting performance.

## How it works

- One entry point: `complete(task=..., system=..., user=..., max_tokens=...)`.
- Each *task* is routed through an ordered chain of `provider:model`
  candidates. They're tried left to right; if the first errors, times out, or
  is rate limited, the next one serves the request.
- **Happy path = one call, zero added latency.** Failover only fires on an
  actual error. A per-call timeout (`LLM_TIMEOUT`) means a hung provider fails
  fast to the backup instead of stalling the 2-minute cron.

Tasks: `classify`, `reply`, `objection`, `draft`, `brief`, `research`.

## Providers

| Provider    | How to enable | Covers |
|-------------|---------------|--------|
| `anthropic` | `ANTHROPIC_API_KEY` (primary) | Claude models |
| `openai`    | `OPENAI_API_KEY` | OpenAI **and** any OpenAI-compatible API via `OPENAI_BASE_URL` — OpenRouter, Groq, DeepSeek, Together, Google's OpenAI-compatible endpoint, or a local Ollama / LM Studio server |

One adapter + `OPENAI_BASE_URL` unlocks dozens of cheap or backup models.

## Defaults (no config = no change)

If you set nothing, **every task stays on the primary Claude model**
(`LLM_MODEL`, default `claude-sonnet-4-6`) — identical quality to before. If
`OPENAI_API_KEY` is set, OpenAI is added automatically as a backup *only*; it
never serves traffic unless Claude fails.

## Adding a backup (resilience)

In `.env`:

```
OPENAI_API_KEY=sk-...
# optional: point at a cheaper compatible provider instead of OpenAI
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

That's it — if Claude is down, the engine keeps running on the backup.

## Saving money (per-task routes)

Route bulk/cheap tasks to cheaper models. The classifier and company research
are the best candidates; keep customer-facing replies on the strong model so
quality is untouched:

```
LLM_ROUTE_CLASSIFY=anthropic:claude-haiku-4-5-20251001, openai:gpt-4o-mini
LLM_ROUTE_RESEARCH=openai:gpt-4o-mini, anthropic:claude-sonnet-4-6
LLM_ROUTE_REPLY=anthropic:claude-sonnet-4-6, openai:gpt-4o
```

Format: comma-separated `provider:model`, tried left to right. A candidate is
skipped if its provider has no key, so the same `.env` works with or without a
backup configured.

## Tuning

| Var | Default | Meaning |
|-----|---------|---------|
| `LLM_MODEL` | `claude-sonnet-4-6` | Primary model |
| `LLM_MODEL_FAST` | `claude-haiku-4-5-20251001` | Cheaper Claude model for cost routes |
| `OPENAI_MODEL` / `OPENAI_MODEL_FAST` | `gpt-4o` / `gpt-4o-mini` | Backup models |
| `LLM_TIMEOUT` | `30` | Per-call timeout (seconds) |
| `LLM_MAX_RETRIES` | `2` | Transient-error retries before failing over |

## Verify

```
python scripts/test_connections.py
```

The first check now exercises the full routed stack (and prints which
providers are configured).
