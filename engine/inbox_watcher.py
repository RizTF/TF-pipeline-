#!/usr/bin/env python3
"""
TalentFinder Inbox Watcher
==========================
Runs every 2 minutes via cron. Checks Paul's inbox for new replies,
classifies them with Claude, and takes the appropriate action.

Actions by category:
  POSITIVE        → auto-reply + suppress AC + notify Riz
  QUESTION        → auto-reply + notify Riz
  COMPLEX         → draft for Riz approval via Telegram
  NOT_INTERESTED  → suppress AC + polite close + log
  UNSUBSCRIBE     → hard unsubscribe from AC + log
  WRONG_PERSON    → suppress AC + tag + log
  BOOKING         → pre-call brief → Riz on Telegram
  AUTO_REPLY      → silently ignore
"""

import json
import logging
import sys
import re
from datetime import datetime
from pathlib import Path

# Ensure engine root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import PENDING_DRAFTS_FILE
from modules.imap_client import fetch_new_emails, send_reply
from modules.claude_client import (
    classify_email,
    generate_reply,
    generate_draft,
    generate_precall_brief,
    generate_objection_reply,
)
from modules.conversation_store import (
    add_inbound,
    add_outbound,
    format_history_for_prompt,
)
from modules.company_research import research_company
from modules.telegram_client import (
    notify_positive,
    notify_complex,
    notify_booking,
    notify_question_answered,
)
from modules.sheets_client import log_email
from modules.ac_client import suppress_contact, hard_unsubscribe

# ── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tf.watcher")


# ── Helpers ──────────────────────────────────────────────────────────

def _extract_email(from_field: str) -> str:
    """Extract bare email from 'Name <email@example.com>' format."""
    match = re.search(r"<(.+?)>", from_field)
    return match.group(1) if match else from_field


def _load_drafts() -> dict:
    if PENDING_DRAFTS_FILE.exists():
        return json.loads(PENDING_DRAFTS_FILE.read_text())
    return {}


def _save_drafts(drafts: dict) -> None:
    PENDING_DRAFTS_FILE.write_text(json.dumps(drafts, indent=2))


def _next_draft_id(drafts: dict) -> str:
    existing = [int(k.split("_")[1]) for k in drafts if k.startswith("draft_")]
    next_num = max(existing, default=0) + 1
    return f"draft_{next_num}"


# ── Main processing ─────────────────────────────────────────────────

def process_email(email_data: dict) -> None:
    """Process a single inbound email through the full pipeline."""
    from_addr = email_data["from"]
    sender_email = _extract_email(from_addr)
    subject = email_data["subject"]
    body = email_data["body"]
    message_id = email_data.get("message_id", "")

    logger.info(f"Processing: {from_addr} — {subject}")

    # Step 1: Classify with Claude
    result = classify_email(from_addr, subject, body)
    category = result.get("category", "COMPLEX")
    confidence = result.get("confidence", 0.0)
    sender_name = result.get("sender_name", "")
    sender_company = result.get("sender_company", "")
    summary = result.get("summary", "")
    urgency = result.get("urgency", "MEDIUM")

    logger.info(f"Classified as {category} (confidence: {confidence})")

    # Get conversation history for threading
    history = format_history_for_prompt(sender_email)

    # Record this inbound email
    add_inbound(sender_email, subject, body, category)

    action_taken = ""

    # Step 2: Act based on category
    if category == "AUTO_REPLY":
        action_taken = "Ignored (auto-reply/bounce)"
        logger.info("Auto-reply detected — ignoring")

    elif category == "POSITIVE":
        reply_text = generate_reply(from_addr, subject, body, category, history=history)
        if reply_text:
            reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
            sent = send_reply(sender_email, reply_subject, reply_text, message_id)
            action_taken = "Auto-reply sent" if sent else "Reply generation failed"
            if sent:
                add_outbound(sender_email, reply_subject, reply_text)
        suppress_contact(sender_email, "positive-reply")
        notify_positive(sender_name, sender_company, subject, summary)

    elif category == "QUESTION":
        reply_text = generate_reply(from_addr, subject, body, category, history=history)
        if reply_text:
            reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
            sent = send_reply(sender_email, reply_subject, reply_text, message_id)
            action_taken = "Question auto-answered" if sent else "Reply failed"
            if sent:
                add_outbound(sender_email, reply_subject, reply_text)
        notify_question_answered(sender_name, subject, summary)

    elif category == "COMPLEX":
        draft_text = generate_draft(from_addr, subject, body, summary, history=history)
        drafts = _load_drafts()
        draft_id = _next_draft_id(drafts)
        drafts[draft_id] = {
            "to": sender_email,
            "subject": f"Re: {subject}" if not subject.startswith("Re:") else subject,
            "body": draft_text,
            "in_reply_to": message_id,
            "created": datetime.now().isoformat(),
        }
        _save_drafts(drafts)
        notify_complex(
            draft_id, sender_name, sender_company, subject, summary, draft_text
        )
        action_taken = f"Draft created ({draft_id}) — awaiting approval"

    elif category == "NOT_INTERESTED":
        # Research the company for personalised objection handling
        logger.info(f"Researching {sender_company or sender_email} for objection handling...")
        company_info = research_company(sender_email, sender_name, sender_company)

        # Generate smart objection-handling reply instead of generic polite close
        reply_text = generate_objection_reply(
            from_addr, subject, body,
            history=history, company_research=company_info
        )
        if reply_text:
            reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject

            # Create as draft for Riz to review — objection handling needs human approval
            drafts = _load_drafts()
            draft_id = _next_draft_id(drafts)
            drafts[draft_id] = {
                "to": sender_email,
                "subject": reply_subject,
                "body": reply_text,
                "in_reply_to": message_id,
                "created": datetime.now().isoformat(),
                "type": "objection_handling",
            }
            _save_drafts(drafts)
            notify_complex(
                draft_id, sender_name, sender_company, subject,
                f"NOT INTERESTED — objection handling draft with company research",
                reply_text,
            )
            action_taken = f"Objection draft created ({draft_id}) — awaiting approval"
        else:
            action_taken = "NOT_INTERESTED — objection reply failed"

        suppress_contact(sender_email, "not-interested")

    elif category == "UNSUBSCRIBE":
        hard_unsubscribe(sender_email)
        action_taken = "Hard unsubscribed from AC"

    elif category == "WRONG_PERSON":
        suppress_contact(sender_email, "wrong-person")
        action_taken = "Suppressed + tagged wrong-person"

    elif category == "BOOKING_CONFIRMED":
        brief = generate_precall_brief(from_addr, subject, body)
        notify_booking(sender_name, sender_company, brief)
        action_taken = "Pre-call brief sent to Riz"

    # Step 3: Log to Google Sheets
    log_email(
        from_addr=sender_email,
        name=sender_name,
        company=sender_company,
        subject=subject,
        category=category,
        summary=summary,
        urgency=urgency,
        action=action_taken,
        confidence=confidence,
    )

    logger.info(f"Done: {action_taken}")


def main():
    logger.info("=== Inbox watcher run started ===")
    emails = fetch_new_emails()

    if not emails:
        logger.info("No new emails")
        return

    logger.info(f"Processing {len(emails)} new email(s)")
    for email_data in emails:
        try:
            process_email(email_data)
        except Exception as e:
            logger.error(f"Error processing email from {email_data.get('from')}: {e}")

    logger.info("=== Inbox watcher run complete ===")


if __name__ == "__main__":
    main()
