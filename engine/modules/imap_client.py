"""
Email client — reads Paul's Outlook inbox via Microsoft Graph API
and sends replies via SMTP.

Graph API is used for reading because M365 blocks basic auth on IMAP.
SMTP with basic auth still works for sending.
"""

import json
import logging
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests

from config.settings import (
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    PROCESSED_UIDS_FILE,
)

logger = logging.getLogger("tf.imap")

# Microsoft Graph endpoints
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2/token"


def _load_processed_uids() -> set:
    if PROCESSED_UIDS_FILE.exists():
        return set(json.loads(PROCESSED_UIDS_FILE.read_text()))
    return set()


def _save_processed_uids(uids: set) -> None:
    PROCESSED_UIDS_FILE.write_text(json.dumps(sorted(uids)))


def _get_graph_token() -> Optional[str]:
    """Get an OAuth2 access token for Microsoft Graph using client credentials."""
    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]):
        logger.warning("Azure credentials not set — cannot use Graph API")
        return None

    try:
        resp = requests.post(
            TOKEN_URL.format(tenant=AZURE_TENANT_ID),
            data={
                "client_id": AZURE_CLIENT_ID,
                "client_secret": AZURE_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        logger.error(f"Graph token error: {e}")
        return None


def fetch_new_emails() -> list[dict]:
    """
    Fetch unread emails from Paul's inbox via Microsoft Graph API.
    Returns list of dicts with email metadata + body.
    """
    token = _get_graph_token()
    if not token:
        return []

    processed = _load_processed_uids()
    new_emails = []
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Fetch unread messages
        url = (
            f"{GRAPH_BASE}/users/{EMAIL_ADDRESS}/messages"
            f"?$filter=isRead eq false"
            f"&$select=id,from,subject,body,receivedDateTime,internetMessageId"
            f"&$top=50"
            f"&$orderby=receivedDateTime desc"
        )
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        messages = resp.json().get("value", [])

        logger.info(f"Found {len(messages)} unread emails")

        for msg in messages:
            msg_id = msg["id"]
            if msg_id in processed:
                continue

            from_data = msg.get("from", {}).get("emailAddress", {})
            from_addr = f"{from_data.get('name', '')} <{from_data.get('address', '')}>"
            subject = msg.get("subject", "")
            body = msg.get("body", {}).get("content", "")
            # Strip HTML tags for plain text
            if msg.get("body", {}).get("contentType") == "html":
                import re
                body = re.sub(r"<[^>]+>", " ", body)
                body = re.sub(r"\s+", " ", body).strip()

            new_emails.append({
                "uid": msg_id,
                "from": from_addr,
                "subject": subject,
                "body": body[:3000],
                "date": msg.get("receivedDateTime", ""),
                "message_id": msg.get("internetMessageId", ""),
            })

            # Mark as read in Outlook
            try:
                requests.patch(
                    f"{GRAPH_BASE}/users/{EMAIL_ADDRESS}/messages/{msg_id}",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"isRead": True},
                    timeout=10,
                )
            except Exception:
                pass

            processed.add(msg_id)

        _save_processed_uids(processed)

    except Exception as e:
        logger.error(f"Graph API error: {e}")

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


def test_graph_connection() -> bool:
    """Test that Graph API can read Paul's inbox."""
    token = _get_graph_token()
    if not token:
        return False
    try:
        resp = requests.get(
            f"{GRAPH_BASE}/users/{EMAIL_ADDRESS}/messages?$top=1&$select=id",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Graph API test failed: {e}")
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
