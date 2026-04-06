#!/usr/bin/env python3
"""
TalentFinder Telegram Handler
==============================
Runs every 2 minutes via cron. Processes commands from Riz via Telegram.

Draft Commands:
  SEND draft_1          → sends the draft reply from Paul's inbox
  SKIP draft_1          → discards the draft, no reply sent
  EDIT draft_1 <text>   → replace draft body and send

System Commands:
  STATUS                → system health overview
  DRAFTS                → list all pending drafts
  LOGS                  → last 10 log entries
  QUEUE                 → show emails waiting in webhook queue
  HISTORY <email>       → conversation history for a sender
  STATS                 → processing statistics
  PAUSE                 → pause email processing
  RESUME                → resume email processing
  TEST                  → run connection tests
  HELP                  → show all commands
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import PENDING_DRAFTS_FILE, DATA_DIR, LOGS_DIR, TELEGRAM_CHAT_ID, ENGINE_ROOT
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
PAUSE_FILE = DATA_DIR / "paused.flag"
INCOMING_FILE = DATA_DIR / "incoming_emails.json"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
LOG_FILE = LOGS_DIR / "inbox_watcher.log"


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


# ── Draft Commands ───────────────────────────────────────────────────

def cmd_send(draft_id: str) -> None:
    drafts = _load_drafts()
    if draft_id not in drafts:
        send_message(f"Draft <code>{draft_id}</code> not found.")
        return
    draft = drafts[draft_id]
    success = send_reply(
        to_address=draft["to"],
        subject=draft["subject"],
        body=draft["body"],
        in_reply_to=draft.get("in_reply_to"),
    )
    if success:
        # Track outbound in conversation store
        try:
            from modules.conversation_store import add_outbound
            add_outbound(draft["to"], draft["subject"], draft["body"])
        except Exception:
            pass
        send_message(f"Sent reply to {draft['to']}")
        del drafts[draft_id]
        _save_drafts(drafts)
    else:
        send_message(f"Failed to send reply to {draft['to']} — check email credentials")


def cmd_edit(draft_id: str, new_body: str) -> None:
    drafts = _load_drafts()
    if draft_id not in drafts:
        send_message(f"Draft <code>{draft_id}</code> not found.")
        return
    draft = drafts[draft_id]
    success = send_reply(
        to_address=draft["to"],
        subject=draft["subject"],
        body=new_body,
        in_reply_to=draft.get("in_reply_to"),
    )
    if success:
        try:
            from modules.conversation_store import add_outbound
            add_outbound(draft["to"], draft["subject"], new_body)
        except Exception:
            pass
        send_message(f"Edited and sent reply to {draft['to']}")
        del drafts[draft_id]
        _save_drafts(drafts)
    else:
        send_message(f"Failed to send edited reply to {draft['to']}")


def cmd_skip(draft_id: str) -> None:
    drafts = _load_drafts()
    if draft_id not in drafts:
        send_message(f"Draft <code>{draft_id}</code> not found.")
        return
    to = drafts[draft_id]["to"]
    del drafts[draft_id]
    _save_drafts(drafts)
    send_message(f"Skipped draft for {to} — no reply sent.")


# ── System Commands ──────────────────────────────────────────────────

def cmd_status() -> None:
    """Full system health overview."""
    # Webhook server
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "tf-webhook"],
            capture_output=True, text=True, timeout=5
        )
        webhook = result.stdout.strip()
    except Exception:
        webhook = "unknown"

    # Queue size
    try:
        emails = json.loads(INCOMING_FILE.read_text()) if INCOMING_FILE.exists() else []
        queue_size = len(emails)
    except Exception:
        queue_size = "error"

    # Pending drafts
    drafts = _load_drafts()
    draft_count = len(drafts)

    # Last log entry
    try:
        lines = LOG_FILE.read_text().strip().split("\n")
        last_log = lines[-1][:80] if lines else "No logs"
    except Exception:
        last_log = "No logs"

    # Paused?
    paused = PAUSE_FILE.exists()

    # Conversations tracked
    try:
        convos = json.loads(CONVERSATIONS_FILE.read_text()) if CONVERSATIONS_FILE.exists() else {}
        convo_count = len(convos)
    except Exception:
        convo_count = 0

    msg = (
        f"<b>TF ENGINE STATUS</b>\n\n"
        f"{'⏸ PAUSED' if paused else '▶️ RUNNING'}\n\n"
        f"<b>Webhook server:</b> {webhook}\n"
        f"<b>Emails in queue:</b> {queue_size}\n"
        f"<b>Pending drafts:</b> {draft_count}\n"
        f"<b>Conversations tracked:</b> {convo_count}\n"
        f"<b>Last log:</b> <code>{last_log}</code>\n"
        f"<b>Time:</b> {datetime.now().strftime('%H:%M %d/%m/%Y')}"
    )
    send_message(msg)


def cmd_drafts() -> None:
    """List all pending drafts."""
    drafts = _load_drafts()
    if not drafts:
        send_message("No pending drafts.")
        return

    lines = ["<b>PENDING DRAFTS</b>\n"]
    for draft_id, draft in drafts.items():
        created = draft.get("created", "unknown")[:16]
        draft_type = draft.get("type", "standard")
        lines.append(
            f"<b>{draft_id}</b> → {draft['to']}\n"
            f"  Subject: {draft['subject'][:50]}\n"
            f"  Type: {draft_type} | Created: {created}\n"
            f"  <code>SEND {draft_id}</code> | <code>SKIP {draft_id}</code>"
        )

    send_message("\n\n".join(lines))


def cmd_logs(count: int = 10) -> None:
    """Show last N log entries."""
    try:
        lines = LOG_FILE.read_text().strip().split("\n")
        recent = lines[-count:] if len(lines) >= count else lines
        msg = "<b>RECENT LOGS</b>\n\n<code>" + "\n".join(recent) + "</code>"
        send_message(msg[:4000])
    except Exception as e:
        send_message(f"Error reading logs: {e}")


def cmd_queue() -> None:
    """Show emails waiting in the webhook queue."""
    try:
        emails = json.loads(INCOMING_FILE.read_text()) if INCOMING_FILE.exists() else []
        if not emails:
            send_message("Queue is empty — no emails waiting.")
            return

        lines = [f"<b>QUEUED EMAILS ({len(emails)})</b>\n"]
        for em in emails[:10]:  # Show max 10
            lines.append(
                f"From: {em.get('from', 'unknown')}\n"
                f"Subject: {em.get('subject', 'no subject')[:60]}"
            )
        send_message("\n\n".join(lines))
    except Exception as e:
        send_message(f"Error reading queue: {e}")


def cmd_history(email_addr: str) -> None:
    """Show conversation history for a sender."""
    try:
        from modules.conversation_store import get_history
        history = get_history(email_addr)
        if not history:
            send_message(f"No conversation history for {email_addr}")
            return

        lines = [f"<b>HISTORY: {email_addr}</b>\n"]
        for entry in history[-5:]:  # Last 5 exchanges
            direction = "⬅️ THEM" if entry["direction"] == "inbound" else "➡️ PAUL"
            ts = entry.get("timestamp", "")[:16]
            body_preview = entry["body"][:150].replace("<", "&lt;")
            lines.append(f"{direction} ({ts})\n{body_preview}...")

        send_message("\n\n".join(lines)[:4000])
    except Exception as e:
        send_message(f"Error: {e}")


def cmd_stats() -> None:
    """Processing statistics from logs."""
    try:
        log_text = LOG_FILE.read_text() if LOG_FILE.exists() else ""
        total = log_text.count("Processing:")
        positive = log_text.count("POSITIVE")
        question = log_text.count("QUESTION")
        complex_ = log_text.count("COMPLEX")
        not_interested = log_text.count("NOT_INTERESTED")
        auto_reply = log_text.count("AUTO_REPLY")
        unsubscribe = log_text.count("UNSUBSCRIBE")

        # Count conversations
        try:
            convos = json.loads(CONVERSATIONS_FILE.read_text()) if CONVERSATIONS_FILE.exists() else {}
            convo_count = len(convos)
        except Exception:
            convo_count = 0

        msg = (
            f"<b>PROCESSING STATS</b>\n\n"
            f"<b>Total emails processed:</b> {total}\n"
            f"<b>Positive:</b> {positive}\n"
            f"<b>Questions:</b> {question}\n"
            f"<b>Complex:</b> {complex_}\n"
            f"<b>Not interested:</b> {not_interested}\n"
            f"<b>Auto-replies:</b> {auto_reply}\n"
            f"<b>Unsubscribes:</b> {unsubscribe}\n"
            f"<b>Active conversations:</b> {convo_count}"
        )
        send_message(msg)
    except Exception as e:
        send_message(f"Error: {e}")


def cmd_pause() -> None:
    """Pause email processing."""
    PAUSE_FILE.write_text(datetime.now().isoformat())
    send_message("⏸ <b>Engine PAUSED</b>\n\nEmail processing is paused. Send <code>RESUME</code> to restart.")


def cmd_resume() -> None:
    """Resume email processing."""
    if PAUSE_FILE.exists():
        PAUSE_FILE.unlink()
    send_message("▶️ <b>Engine RESUMED</b>\n\nEmail processing is active again.")


def cmd_test() -> None:
    """Run connection tests."""
    send_message("Running connection tests...")
    try:
        venv_python = ENGINE_ROOT / "venv" / "bin" / "python"
        test_script = ENGINE_ROOT / "scripts" / "test_connections.py"
        result = subprocess.run(
            [str(venv_python), str(test_script)],
            capture_output=True, text=True, timeout=30,
            cwd=str(ENGINE_ROOT),
        )
        output = result.stdout[-3000:] if result.stdout else "No output"
        if result.stderr:
            output += f"\n\nErrors:\n{result.stderr[-500:]}"
        send_message(f"<b>CONNECTION TESTS</b>\n\n<code>{output}</code>"[:4000])
    except Exception as e:
        send_message(f"Test error: {e}")


def cmd_help() -> None:
    """Show all available commands."""
    msg = (
        "<b>TF ENGINE COMMANDS</b>\n\n"
        "<b>— Draft Management —</b>\n"
        "<code>SEND draft_1</code> — Send draft as-is\n"
        "<code>EDIT draft_1 text</code> — Replace and send\n"
        "<code>SKIP draft_1</code> — Discard draft\n"
        "<code>DRAFTS</code> — List all pending drafts\n\n"
        "<b>— System —</b>\n"
        "<code>STATUS</code> — System health overview\n"
        "<code>LOGS</code> — Last 10 log entries\n"
        "<code>LOGS 20</code> — Last 20 log entries\n"
        "<code>QUEUE</code> — Show queued emails\n"
        "<code>STATS</code> — Processing statistics\n"
        "<code>TEST</code> — Run connection tests\n\n"
        "<b>— Conversations —</b>\n"
        "<code>HISTORY email@example.com</code> — Sender history\n\n"
        "<b>— Control —</b>\n"
        "<code>PAUSE</code> — Pause email processing\n"
        "<code>RESUME</code> — Resume email processing\n"
        "<code>HELP</code> — This message"
    )
    send_message(msg)


# ── Command Router ───────────────────────────────────────────────────

def route_command(text: str) -> None:
    """Route a Telegram message to the correct command handler."""
    text = text.strip()
    upper = text.upper()
    parts = text.split(None, 1)
    cmd = parts[0].upper() if parts else ""
    args = parts[1].strip() if len(parts) > 1 else ""

    # Draft commands
    if cmd == "SEND" and args:
        cmd_send(args)
    elif cmd == "SKIP" and args:
        cmd_skip(args)
    elif cmd == "EDIT" and args:
        edit_parts = args.split(None, 1)
        if len(edit_parts) >= 2:
            cmd_edit(edit_parts[0], edit_parts[1])
        else:
            send_message("Usage: <code>EDIT draft_1 Your replacement text here</code>")

    # System commands
    elif cmd == "STATUS":
        cmd_status()
    elif cmd == "DRAFTS":
        cmd_drafts()
    elif cmd == "LOGS":
        count = 10
        if args and args.isdigit():
            count = min(int(args), 50)
        cmd_logs(count)
    elif cmd == "QUEUE":
        cmd_queue()
    elif cmd == "HISTORY" and args:
        cmd_history(args)
    elif cmd == "STATS":
        cmd_stats()
    elif cmd == "PAUSE":
        cmd_pause()
    elif cmd == "RESUME":
        cmd_resume()
    elif cmd == "TEST":
        cmd_test()
    elif cmd == "HELP":
        cmd_help()
    else:
        send_message(
            f"Unknown command: <code>{text[:50]}</code>\n\n"
            f"Send <code>HELP</code> for available commands."
        )


# ── Main ─────────────────────────────────────────────────────────────

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

        if text:
            logger.info(f"Processing command: {text[:50]}")
            route_command(text)

        _save_offset(update_id + 1)

    logger.info("=== Telegram handler run complete ===")


if __name__ == "__main__":
    main()
