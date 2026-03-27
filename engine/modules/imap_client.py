"""
Email client — reads incoming emails from the webhook queue
and sends replies via SMTP.

Incoming emails arrive via webhook_server.py (Power Automate forwards
Paul's emails to http://VPS_IP:5111/incoming). This module reads from
the queue file and clears processed entries.

SMTP with basic auth is used for sending replies (still works on M365).
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
    DATA_DIR,
)

logger = logging.getLogger("tf.imap")

INCOMING_FILE = DATA_DIR / "incoming_emails.json"


def fetch_new_emails() -> list[dict]:
    """
    Read queued emails from the webhook incoming file.
    Clears the queue after reading.
    """
    if not INCOMING_FILE.exists():
        return []

    try:
        raw = INCOMING_FILE.read_text().strip()
        if not raw:
            return []

        emails = json.loads(raw)
        if not emails:
            return []

        # Clear the queue
        INCOMING_FILE.write_text("[]")

        logger.info(f"Picked up {len(emails)} email(s) from webhook queue")
        return emails

    except Exception as e:
        logger.error(f"Error reading webhook queue: {e}")
        return []


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


def test_webhook_queue() -> bool:
    """Test that the webhook queue file is accessible."""
    try:
        if not INCOMING_FILE.exists():
            INCOMING_FILE.write_text("[]")
        json.loads(INCOMING_FILE.read_text())
        return True
    except Exception as e:
        logger.error(f"Webhook queue test failed: {e}")
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
