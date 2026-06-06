"""
TalentFinder Sales Engine — Settings
Loads all configuration from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from engine root
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def _require(key: str) -> str:
    """Return env var or raise clear error."""
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {key}  — check your .env file")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# --- AI / LLM providers ---
# Anthropic is the primary provider. Other providers are optional and act as
# cheaper routes and/or automatic backups if Anthropic is unavailable.
# See modules/llm.py for the provider-agnostic routing + failover layer.
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# Primary model. Defaults to the current Claude Sonnet (closes the migration
# off the deprecated claude-sonnet-4-20250514 snapshot).
LLM_MODEL = _optional("LLM_MODEL", "claude-sonnet-4-6")
# Cheaper/faster model, available for cost-saving task routes (see .env.example).
LLM_MODEL_FAST = _optional("LLM_MODEL_FAST", "claude-haiku-4-5-20251001")

# Backwards-compatible alias — older code may still import CLAUDE_MODEL.
CLAUDE_MODEL = LLM_MODEL

# Optional OpenAI-compatible provider (OpenAI, OpenRouter, Groq, DeepSeek,
# Together, Google OpenAI-compat, or a local Ollama/LM Studio server). Leave
# OPENAI_API_KEY blank to disable — the engine then runs Anthropic-only.
OPENAI_API_KEY = _optional("OPENAI_API_KEY")
OPENAI_BASE_URL = _optional("OPENAI_BASE_URL")  # blank = api.openai.com
OPENAI_MODEL = _optional("OPENAI_MODEL", "gpt-4o")
OPENAI_MODEL_FAST = _optional("OPENAI_MODEL_FAST", "gpt-4o-mini")

# Per-call timeout (seconds) so a hung provider fails fast to the backup,
# and how many times to retry a transient error before failing over.
LLM_TIMEOUT = float(_optional("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(_optional("LLM_MAX_RETRIES", "2"))

# --- Email ---
SMTP_SERVER = _optional("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(_optional("SMTP_PORT", "587"))
EMAIL_ADDRESS = _require("EMAIL_ADDRESS")
EMAIL_PASSWORD = _optional("EMAIL_PASSWORD")


# --- Telegram ---
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _optional("TELEGRAM_CHAT_ID")

# --- ActiveCampaign ---
AC_API_URL = _optional("AC_API_URL")
AC_API_KEY = _optional("AC_API_KEY")

# --- Google Sheets ---
GOOGLE_SHEETS_ID = _optional("GOOGLE_SHEETS_ID")
GOOGLE_CREDENTIALS_FILE = _optional(
    "GOOGLE_CREDENTIALS_FILE",
    str(Path(__file__).resolve().parent / "google_credentials.json"),
)

# --- Calendly ---
CALENDLY_LINK = _optional(
    "CALENDLY_LINK", "https://calendly.com/talent-finder/recruitment-clone"
)

# --- Paths ---
ENGINE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ENGINE_ROOT / "data"
LOGS_DIR = ENGINE_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# File that tracks which email UIDs we have already processed
PROCESSED_UIDS_FILE = DATA_DIR / "processed_uids.json"
# File that stores pending drafts awaiting Riz's approval
PENDING_DRAFTS_FILE = DATA_DIR / "pending_drafts.json"
