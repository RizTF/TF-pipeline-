"""
Telegram bot client — sends notifications to Riz and handles approvals.
"""

import json
import logging
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("tf.telegram")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, chat_id: str = "") -> bool:
    """Send a Telegram message to Riz."""
    cid = chat_id or TELEGRAM_CHAT_ID
    if not cid:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping notification")
        return False

    try:
        resp = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": cid,
                "text": text[:4096],  # Telegram limit
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


def notify_positive(sender: str, company: str, subject: str, summary: str) -> bool:
    """Notify Riz of a positive reply — auto-handled."""
    msg = (
        f"<b>POSITIVE REPLY</b>\n\n"
        f"<b>From:</b> {sender}\n"
        f"<b>Company:</b> {company}\n"
        f"<b>Subject:</b> {subject}\n"
        f"<b>Summary:</b> {summary}\n\n"
        f"Auto-reply sent from Paul's inbox. AC sequence suppressed."
    )
    return send_message(msg)


def notify_complex(
    draft_id: str, sender: str, company: str, subject: str, summary: str, draft: str
) -> bool:
    """Send a COMPLEX draft for Riz's approval."""
    msg = (
        f"<b>NEEDS YOUR REVIEW</b>\n\n"
        f"<b>From:</b> {sender}\n"
        f"<b>Company:</b> {company}\n"
        f"<b>Subject:</b> {subject}\n"
        f"<b>Summary:</b> {summary}\n\n"
        f"<b>Draft reply:</b>\n<i>{draft[:2000]}</i>\n\n"
        f"Reply <code>SEND {draft_id}</code> to send as-is.\n"
        f"Reply <code>EDIT {draft_id} your text here</code> to edit and send.\n"
        f"Reply <code>SKIP {draft_id}</code> to discard."
    )
    return send_message(msg)


def notify_booking(sender: str, company: str, brief: str) -> bool:
    """Send pre-call brief to Riz."""
    msg = (
        f"<b>BOOKING CONFIRMED</b>\n\n"
        f"<b>From:</b> {sender}\n"
        f"<b>Company:</b> {company}\n\n"
        f"<b>Pre-call brief:</b>\n{brief}"
    )
    return send_message(msg)


def notify_question_answered(sender: str, subject: str, summary: str) -> bool:
    """Inform Riz that a question was auto-answered."""
    msg = (
        f"<b>QUESTION AUTO-ANSWERED</b>\n\n"
        f"<b>From:</b> {sender}\n"
        f"<b>Subject:</b> {subject}\n"
        f"<b>Summary:</b> {summary}\n\n"
        f"Reply sent from Paul's inbox."
    )
    return send_message(msg)


def get_updates(offset: int = 0) -> list[dict]:
    """Fetch new messages sent to the bot (for SEND/SKIP commands)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        logger.error(f"Telegram getUpdates error: {e}")
        return []


def test_connection() -> bool:
    """Quick test that the bot token is valid."""
    try:
        resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Telegram bot: @{data['result']['username']}")
        return data.get("ok", False)
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return False
