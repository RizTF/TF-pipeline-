"""
Email client — reads Paul's Outlook inbox via EWS (Exchange Web Services)
and sends replies via SMTP.

EWS is used for reading because M365 blocks basic auth on IMAP.
SMTP with basic auth still works for sending.
"""

import json
import logging
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config.settings import (
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    PROCESSED_UIDS_FILE,
)

logger = logging.getLogger("tf.imap")


def _load_processed_uids() -> set:
    if PROCESSED_UIDS_FILE.exists():
        return set(json.loads(PROCESSED_UIDS_FILE.read_text()))
    return set()


def _save_processed_uids(uids: set) -> None:
    PROCESSED_UIDS_FILE.write_text(json.dumps(sorted(uids)))


def _get_ews_account():
    """Connect to Paul's mailbox via EWS."""
    from exchangelib import Credentials, Account, Configuration, DELEGATE

    creds = Credentials(username=EMAIL_ADDRESS, password=EMAIL_PASSWORD)
    config = Configuration(server="outlook.office365.com", credentials=creds)
    account = Account(
        primary_smtp_address=EMAIL_ADDRESS,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )
    return account


def fetch_new_emails() -> list[dict]:
    """
    Fetch unread emails from Paul's inbox via EWS.
    Returns list of dicts with email metadata + body.
    """
    if not EMAIL_PASSWORD:
        logger.warning("EMAIL_PASSWORD not set — skipping inbox check")
        return []

    processed = _load_processed_uids()
    new_emails = []

    try:
        account = _get_ews_account()

        # Get unread messages from inbox
        unread = account.inbox.filter(is_read=False).order_by("-datetime_received")[:50]

        count = 0
        for item in unread:
            count += 1
            msg_id = item.message_id or item.id
            if msg_id in processed:
                continue

            from_addr = ""
            if item.sender:
                name = item.sender.name or ""
                addr = item.sender.email_address or ""
                from_addr = f"{name} <{addr}>" if name else addr

            body = ""
            if item.text_body:
                body = item.text_body
            elif item.body:
                import re
                body = re.sub(r"<[^>]+>", " ", str(item.body))
                body = re.sub(r"\s+", " ", body).strip()

            new_emails.append({
                "uid": msg_id,
                "from": from_addr,
                "subject": item.subject or "",
                "body": body[:3000],
                "date": str(item.datetime_received or ""),
                "message_id": item.message_id or "",
            })

            # Mark as read
            item.is_read = True
            item.save(update_fields=["is_read"])

            processed.add(msg_id)

        logger.info(f"Found {count} unread emails, {len(new_emails)} new")
        _save_processed_uids(processed)

    except Exception as e:
        logger.error(f"EWS error: {e}")

    return new_emails


def send_reply(
    to_address: str,
    subject: str,
    body: str,
    in_reply_to: Optional[str] = None,
) -> bool:
    """
    Send an email reply from Paul's Outlook inbox via SMTP.
    Returns True on success.
    """
    if not EMAIL_PASSWORD:
        logger.warning("EMAIL_PASSWORD not set — cannot send email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_address
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent to {to_address}: {subject}")
        return True

    except Exception as e:
        logger.error(f"SMTP error sending to {to_address}: {e}")
        return False


def test_ews_connection() -> bool:
    """Test that EWS can read Paul's inbox."""
    if not EMAIL_PASSWORD:
        return False
    try:
        account = _get_ews_account()
        # Just access inbox to verify connection
        account.inbox.total_count
        return True
    except Exception as e:
        logger.error(f"EWS test failed: {e}")
        return False


def test_smtp_connection() -> bool:
    """Quick test that SMTP login works."""
    if not EMAIL_PASSWORD:
        return False
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        return True
    except Exception as e:
        logger.error(f"SMTP test failed: {e}")
        return False
