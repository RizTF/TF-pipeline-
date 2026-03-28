#!/usr/bin/env python3
"""
TalentFinder Telegram Handler
==============================
Runs every 2 minutes via cron. Checks for SEND/SKIP commands from Riz
and processes them — sending approved drafts or discarding skipped ones.

Commands Riz can send:
  SEND draft_1    → sends the draft reply from Paul's inbox
  SKIP draft_1    → discards the draft, no reply sent
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import PENDING_DRAFTS_FILE, DATA_DIR, TELEGRAM_CHAT_ID
from modules.imap_client import send_reply
from modules.telegram_client import get_updates, send_message

# ── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tf.telegram_handler")

# Track last processed update to avoid re-processing
OFFSET_FILE = DATA_DIR / "telegram_offset.txt"


def _load_offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except ValueError:
            pass
    return 0


def _save_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


def _load_drafts() -> dict:
    if PENDING_DRAFTS_FILE.exists():
        return json.loads(PENDING_DRAFTS_FILE.read_text())
    return {}


def _save_drafts(drafts: dict) -> None:
    PENDING_DRAFTS_FILE.write_text(json.dumps(drafts, indent=2))


def process_command(text: str) -> None:
    """Process a SEND, SKIP, or EDIT command from Riz."""
    parts = text.strip().split(None, 1)
    if len(parts) < 2:
        send_message(
            "Usage:\n"
            "<code>SEND draft_1</code> — send as-is\n"
            "<code>SKIP draft_1</code> — discard\n"
            "<code>EDIT draft_1 your new text here</code> — replace draft body and send"
        )
        return

    command = parts[0].upper()
    remainder = parts[1].strip()

    # EDIT has 3 parts: EDIT draft_id new_body
    if command == "EDIT":
        edit_parts = remainder.split(None, 1)
        if len(edit_parts) < 2:
            send_message("Usage: <code>EDIT draft_1 Your replacement text here</code>")
            return
        draft_id = edit_parts[0]
        new_body = edit_parts[1]
    else:
        draft_id = remainder
        new_body = None

    drafts = _load_drafts()

    if draft_id not in drafts:
        send_message(f"Draft <code>{draft_id}</code> not found. It may have expired or already been processed.")
        return

    draft = drafts[draft_id]

    if command == "SEND":
        success = send_reply(
            to_address=draft["to"],
            subject=draft["subject"],
            body=draft["body"],
            in_reply_to=draft.get("in_reply_to"),
        )
        if success:
            send_message(f"Sent reply to {draft['to']}")
        else:
            send_message(f"Failed to send reply to {draft['to']} — check email credentials")
            return  # Don't delete draft if send failed

    elif command == "EDIT":
        # Update draft body and send
        draft["body"] = new_body
        success = send_reply(
            to_address=draft["to"],
            subject=draft["subject"],
            body=new_body,
            in_reply_to=draft.get("in_reply_to"),
        )
        if success:
            send_message(f"Edited and sent reply to {draft['to']}")
        else:
            send_message(f"Failed to send edited reply to {draft['to']}")
            return

    elif command == "SKIP":
        send_message(f"Skipped draft for {draft['to']} — no reply sent.")

    else:
        send_message(f"Unknown command: {command}. Use SEND, SKIP, or EDIT.")
        return

    # Remove processed draft
    del drafts[draft_id]
    _save_drafts(drafts)


def main():
    logger.info("=== Telegram handler run started ===")
    offset = _load_offset()
    updates = get_updates(offset)

    if not updates:
        logger.info("No new Telegram messages")
        return

    for update in updates:
        update_id = update["update_id"]

        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        # Only process messages from Riz's chat
        if chat_id != TELEGRAM_CHAT_ID:
            logger.info(f"Ignoring message from chat_id {chat_id}")
            _save_offset(update_id + 1)
            continue

        if text.upper().startswith(("SEND ", "SKIP ", "EDIT ")):
            logger.info(f"Processing command: {text}")
            process_command(text)
        else:
            logger.info(f"Ignoring non-command message: {text[:50]}")

        _save_offset(update_id + 1)

    logger.info("=== Telegram handler run complete ===")


if __name__ == "__main__":
    main()
