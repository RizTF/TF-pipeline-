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


# --- Anthropic ---
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# --- Email ---
SMTP_SERVER = _optional("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(_optional("SMTP_PORT", "587"))
EMAIL_ADDRESS = _require("EMAIL_ADDRESS")
EMAIL_PASSWORD = _optional("EMAIL_PASSWORD")

# --- Azure AD (for Microsoft Graph API — reads Paul's inbox) ---
AZURE_TENANT_ID = _optional("AZURE_TENANT_ID")
AZURE_CLIENT_ID = _optional("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = _optional("AZURE_CLIENT_SECRET")

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
