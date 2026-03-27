"""
Google Sheets client — logs all email interactions via Node.js bridge.
Uses subprocess to call sheets_bridge.js because the Google service account
key format is incompatible with Python's google-auth library.
Node.js (googleapis) handles the key correctly.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from config.settings import GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_FILE, ENGINE_ROOT

logger = logging.getLogger("tf.sheets")

BRIDGE_SCRIPT = Path(__file__).parent / "sheets_bridge.js"


def _run_bridge(cmd: str, args: list[str] = None) -> dict:
    """Call the Node.js sheets bridge and return parsed JSON result."""
    command = ["node", str(BRIDGE_SCRIPT), cmd]
    if args:
        command.extend(args)

    env = {
        "GOOGLE_SHEETS_ID": GOOGLE_SHEETS_ID,
        "GOOGLE_CREDENTIALS_FILE": str(Path(GOOGLE_CREDENTIALS_FILE).resolve())
        if not Path(GOOGLE_CREDENTIALS_FILE).is_absolute()
        else GOOGLE_CREDENTIALS_FILE,
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }

    # If credentials path is relative, resolve from engine root
    creds_path = Path(GOOGLE_CREDENTIALS_FILE)
    if not creds_path.is_absolute():
        env["GOOGLE_CREDENTIALS_FILE"] = str(ENGINE_ROOT / GOOGLE_CREDENTIALS_FILE)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ENGINE_ROOT),
            env=env,
        )
        if result.returncode != 0:
            logger.error(f"Bridge error: {result.stderr}")
            return {"ok": False, "error": result.stderr}
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        logger.error("Bridge timeout")
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Bridge call failed: {e}")
        return {"ok": False, "error": str(e)}


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
    if not GOOGLE_SHEETS_ID:
        return False

    row = json.dumps([
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
    ])

    result = _run_bridge("log", [row])
    if result.get("ok"):
        logger.info(f"Logged to Sheets: {from_addr} — {category}")
        return True
    else:
        logger.error(f"Sheets logging error: {result.get('error')}")
        return False


def test_connection() -> bool:
    """Quick test that we can access the sheet."""
    if not GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID not set")
        return False
    result = _run_bridge("test")
    if not result.get("ok"):
        logger.error(f"Sheets test failed: {result.get('error')}")
    return result.get("ok", False)
