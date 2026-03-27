"""
Google Sheets client — logs all email interactions to the Atlas bridge sheet.
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_FILE

logger = logging.getLogger("tf.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_sheet = None


def _load_credentials(creds_path: str) -> Credentials:
    """Load service account credentials, with DER fallback for broken PEM keys."""
    try:
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    except ValueError:
        logger.info("PEM key loading failed, trying DER fallback")

    # DER fallback: manually decode the private key and build credentials
    from cryptography.hazmat.primitives.serialization import load_der_private_key
    from google.auth.crypt._cryptography_rsa import RSASigner

    with open(creds_path) as f:
        info = json.load(f)

    pk_pem = info["private_key"]
    pem_lines = pk_pem.strip().split("\n")
    b64_body = "".join(l for l in pem_lines if not l.startswith("-----"))
    der_bytes = base64.b64decode(b64_body)

    private_key_obj = load_der_private_key(der_bytes, password=None)
    signer = RSASigner(private_key_obj, key_id=info.get("private_key_id"))

    return Credentials(
        signer=signer,
        service_account_email=info["client_email"],
        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
        scopes=SCOPES,
        project_id=info.get("project_id"),
    )


def _get_sheet():
    """Lazy-load the Google Sheet connection."""
    global _client, _sheet
    if _sheet is not None:
        return _sheet

    creds_path = Path(GOOGLE_CREDENTIALS_FILE)
    if not creds_path.exists():
        logger.warning(f"Google credentials file not found: {creds_path}")
        return None

    if not GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID not set")
        return None

    try:
        creds = _load_credentials(str(creds_path))
        _client = gspread.authorize(creds)
        spreadsheet = _client.open_by_key(GOOGLE_SHEETS_ID)

        # Get or create the "Employer Replies" worksheet
        try:
            _sheet = spreadsheet.worksheet("Employer Replies")
        except gspread.exceptions.WorksheetNotFound:
            _sheet = spreadsheet.add_worksheet(
                title="Employer Replies", rows=1000, cols=10
            )
            # Add headers
            _sheet.update(
                "A1:J1",
                [[
                    "Timestamp",
                    "From",
                    "Name",
                    "Company",
                    "Subject",
                    "Category",
                    "Summary",
                    "Urgency",
                    "Action Taken",
                    "Confidence",
                ]],
            )
        return _sheet
    except Exception as e:
        logger.error(f"Google Sheets connection error: {e}")
        return None


def log_email(
    from_addr: str,
    name: str,
    company: str,
    subject: str,
    category: str,
    summary: str,
    urgency: str,
    action: str,
    confidence: float,
) -> bool:
    """Append one row to the Employer Replies sheet."""
    sheet = _get_sheet()
    if sheet is None:
        return False

    try:
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            from_addr,
            name,
            company,
            subject,
            category,
            summary,
            urgency,
            action,
            str(round(confidence, 2)),
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Logged to Sheets: {from_addr} — {category}")
        return True
    except Exception as e:
        logger.error(f"Sheets logging error: {e}")
        return False


def test_connection() -> bool:
    """Quick test that we can read the sheet."""
    sheet = _get_sheet()
    if sheet is None:
        return False
    try:
        sheet.row_values(1)
        return True
    except Exception as e:
        logger.error(f"Sheets test failed: {e}")
        return False
