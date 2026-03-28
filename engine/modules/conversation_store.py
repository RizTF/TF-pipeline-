"""
Conversation store — tracks email history per sender for threading.
Stores the last N exchanges so Claude has full conversation context.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from config.settings import DATA_DIR

logger = logging.getLogger("tf.conversations")

CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
MAX_HISTORY_PER_SENDER = 10  # Keep last 10 exchanges per sender


def _load_conversations() -> dict:
    if CONVERSATIONS_FILE.exists():
        try:
            return json.loads(CONVERSATIONS_FILE.read_text())
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def _save_conversations(convos: dict) -> None:
    CONVERSATIONS_FILE.write_text(json.dumps(convos, indent=2))


def add_inbound(sender_email: str, subject: str, body: str, category: str = "") -> None:
    """Record an inbound email from a sender."""
    convos = _load_conversations()
    key = sender_email.lower().strip()

    if key not in convos:
        convos[key] = []

    convos[key].append({
        "direction": "inbound",
        "subject": subject,
        "body": body[:2000],  # Cap body size
        "category": category,
        "timestamp": datetime.now().isoformat(),
    })

    # Trim to max history
    convos[key] = convos[key][-MAX_HISTORY_PER_SENDER:]
    _save_conversations(convos)


def add_outbound(sender_email: str, subject: str, body: str) -> None:
    """Record an outbound reply we sent."""
    convos = _load_conversations()
    key = sender_email.lower().strip()

    if key not in convos:
        convos[key] = []

    convos[key].append({
        "direction": "outbound",
        "subject": subject,
        "body": body[:2000],
        "timestamp": datetime.now().isoformat(),
    })

    convos[key] = convos[key][-MAX_HISTORY_PER_SENDER:]
    _save_conversations(convos)


def get_history(sender_email: str) -> list[dict]:
    """Get conversation history for a sender."""
    convos = _load_conversations()
    key = sender_email.lower().strip()
    return convos.get(key, [])


def format_history_for_prompt(sender_email: str) -> str:
    """Format conversation history as text for Claude prompts."""
    history = get_history(sender_email)
    if not history:
        return ""

    lines = ["--- PREVIOUS CONVERSATION HISTORY ---"]
    for entry in history:
        direction = "THEM" if entry["direction"] == "inbound" else "PAUL (us)"
        timestamp = entry.get("timestamp", "")[:16]
        lines.append(f"\n[{timestamp}] {direction}:")
        lines.append(f"Subject: {entry['subject']}")
        lines.append(entry["body"][:500])

    lines.append("\n--- END OF HISTORY ---\n")
    return "\n".join(lines)
