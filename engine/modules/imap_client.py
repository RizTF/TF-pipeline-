"""
IMAP / SMTP client — reads Paul's Outlook inbox and sends replies.
"""

import imaplib
import smtplib
import email
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional

from config.settings import (
    IMAP_SERVER,
    IMAP_PORT,
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


def _decode_header_value(value: str) -> str:
    """Decode an email header that might be encoded."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and part.get("Content-Disposition") != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: try text/html
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and part.get("Content-Disposition") != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def fetch_new_emails() -> list[dict]:
    """
    Connect to Paul's inbox via IMAP, fetch unread emails we haven't
    processed yet. Returns list of dicts with email metadata + body.
    """
    if not EMAIL_PASSWORD:
        logger.warning("EMAIL_PASSWORD not set — skipping inbox check")
        return []

    processed = _load_processed_uids()
    new_emails = []

    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        imap.select("INBOX")

        # Search for unseen messages
        status, data = imap.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            imap.logout()
            return []

        uids = data[0].split()
        logger.info(f"Found {len(uids)} unread emails")

        for uid_bytes in uids:
            uid = uid_bytes.decode()
            if uid in processed:
                continue

            status, msg_data = imap.fetch(uid_bytes, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_addr = _decode_header_value(msg.get("From", ""))
            subject = _decode_header_value(msg.get("Subject", ""))
            body = _extract_body(msg)
            date_str = msg.get("Date", "")
            message_id = msg.get("Message-ID", "")

            new_emails.append(
                {
                    "uid": uid,
                    "from": from_addr,
                    "subject": subject,
                    "body": body[:3000],  # Truncate very long bodies
                    "date": date_str,
                    "message_id": message_id,
                }
            )

            # Mark as processed
            processed.add(uid)

        _save_processed_uids(processed)
        imap.logout()

    except Exception as e:
        logger.error(f"IMAP error: {e}")

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


def test_imap_connection() -> bool:
    """Quick test that IMAP login works."""
    if not EMAIL_PASSWORD:
        return False
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        imap.logout()
        return True
    except Exception as e:
        logger.error(f"IMAP test failed: {e}")
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
