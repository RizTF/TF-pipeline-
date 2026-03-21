"""
Google Sheets client — logs all email interactions to the Atlas bridge sheet.
"""

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
        creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
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
