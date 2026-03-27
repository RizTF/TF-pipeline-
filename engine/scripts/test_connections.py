#!/usr/bin/env python3
"""
TalentFinder — Connection Tester
=================================
Tests all API connections and reports status.
Run this after filling in .env to verify everything works.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import EMAIL_PASSWORD, AC_API_KEY, GOOGLE_SHEETS_ID


def main():
    print("=" * 50)
    print("  TalentFinder — Connection Test")
    print("=" * 50)
    print()

    results = {}

    # 1. Claude API
    print("Testing Claude API...", end=" ", flush=True)
    try:
        from modules.claude_client import client, CLAUDE_MODEL
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with: CONNECTION OK"}],
        )
        text = response.content[0].text
        if "OK" in text.upper():
            print("OK")
            results["Claude API"] = True
        else:
            print(f"UNEXPECTED: {text}")
            results["Claude API"] = False
    except Exception as e:
        print(f"FAILED — {e}")
        results["Claude API"] = False

    # 2. Telegram
    print("Testing Telegram bot...", end=" ", flush=True)
    try:
        from modules.telegram_client import test_connection
        if test_connection():
            print("OK")
            results["Telegram"] = True
        else:
            print("FAILED")
            results["Telegram"] = False
    except Exception as e:
        print(f"FAILED — {e}")
        results["Telegram"] = False

    # 3. ActiveCampaign
    print("Testing ActiveCampaign...", end=" ", flush=True)
    if not AC_API_KEY:
        print("SKIPPED (AC_API_KEY not set)")
        results["ActiveCampaign"] = None
    else:
        try:
            from modules.ac_client import test_connection as ac_test
            if ac_test():
                print("OK")
                results["ActiveCampaign"] = True
            else:
                print("FAILED")
                results["ActiveCampaign"] = False
        except Exception as e:
            print(f"FAILED — {e}")
            results["ActiveCampaign"] = False

    # 4. Google Sheets
    print("Testing Google Sheets...", end=" ", flush=True)
    if not GOOGLE_SHEETS_ID:
        print("SKIPPED (GOOGLE_SHEETS_ID not set)")
        results["Google Sheets"] = None
    else:
        try:
            from modules.sheets_client import test_connection as sheets_test
            if sheets_test():
                print("OK")
                results["Google Sheets"] = True
            else:
                print("FAILED (check google_credentials.json and sheet sharing)")
                results["Google Sheets"] = False
        except Exception as e:
            print(f"FAILED — {e}")
            results["Google Sheets"] = False

    # 5. Webhook queue (receives Paul's forwarded emails)
    print("Testing webhook queue...", end=" ", flush=True)
    try:
        from modules.imap_client import test_webhook_queue
        if test_webhook_queue():
            print("OK")
            results["Webhook Queue"] = True
        else:
            print("FAILED")
            results["Webhook Queue"] = False
    except Exception as e:
        print(f"FAILED — {e}")
        results["Webhook Queue"] = False

    # 5b. Webhook server running check
    print("Testing webhook server...", end=" ", flush=True)
    try:
        import requests
        resp = requests.get("http://127.0.0.1:5111/health", timeout=3)
        if resp.status_code == 200:
            print(f"OK (queued: {resp.json().get('queued', 0)})")
            results["Webhook Server"] = True
        else:
            print("FAILED (not responding)")
            results["Webhook Server"] = False
    except Exception:
        print("NOT RUNNING (start with: python3 webhook_server.py)")
        results["Webhook Server"] = None

    # 6. SMTP
    print("Testing SMTP (sending emails)...", end=" ", flush=True)
    if not EMAIL_PASSWORD:
        print("SKIPPED (EMAIL_PASSWORD not set)")
        results["SMTP"] = None
    else:
        try:
            from modules.imap_client import test_smtp_connection
            if test_smtp_connection():
                print("OK")
                results["SMTP"] = True
            else:
                print("FAILED")
                results["SMTP"] = False
        except Exception as e:
            print(f"FAILED — {e}")
            results["SMTP"] = False

    # Summary
    print()
    print("=" * 50)
    print("  Summary")
    print("=" * 50)
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for name, status in results.items():
        icon = "PASS" if status is True else ("SKIP" if status is None else "FAIL")
        print(f"  {icon}  {name}")

    print()
    print(f"  {passed} passed, {failed} failed, {skipped} skipped")
    print()

    if failed > 0:
        print("Fix the failures above before going live.")
        sys.exit(1)
    else:
        print("All configured services are working!")
        if skipped > 0:
            print("Skipped services need their credentials added to .env")


if __name__ == "__main__":
    main()
