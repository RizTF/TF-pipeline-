#!/usr/bin/env python3
"""
TalentFinder — Inbound Email Webhook Server
=============================================
Lightweight HTTP server that receives forwarded emails from
Paul's Outlook via Power Automate and queues them for processing.

Runs on port 5111 and accepts POST /incoming with JSON body:
{
    "from": "sender@example.com",
    "from_name": "John Smith",
    "subject": "Re: Recruitment Opportunity",
    "body": "Email body text...",
    "message_id": "<optional-message-id>",
    "date": "2024-01-01T12:00:00Z"
}

Emails are saved to data/incoming_emails.json and picked up
by inbox_watcher.py on its next cron cycle.
"""

import json
import logging
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import DATA_DIR, TELEGRAM_CHAT_ID

INCOMING_FILE = DATA_DIR / "incoming_emails.json"
PORT = 5111

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "logs" / "webhook.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("tf.webhook")


def _load_incoming() -> list:
    if INCOMING_FILE.exists():
        try:
            return json.loads(INCOMING_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _save_incoming(emails: list) -> None:
    INCOMING_FILE.write_text(json.dumps(emails, indent=2))


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/incoming":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"invalid json"}')
            return

        # Build email record
        from_name = data.get("from_name", "")
        from_addr = data.get("from", "")
        email_record = {
            "uid": f"webhook-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(from_addr) % 10000}",
            "from": f"{from_name} <{from_addr}>" if from_name else from_addr,
            "subject": data.get("subject", "(no subject)"),
            "body": data.get("body", "")[:3000],
            "date": data.get("date", datetime.now().isoformat()),
            "message_id": data.get("message_id", ""),
        }

        # Append to queue
        emails = _load_incoming()
        emails.append(email_record)
        _save_incoming(emails)

        logger.info(f"Received: {from_addr} — {email_record['subject']}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "queued": len(emails)}).encode())

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            emails = _load_incoming()
            self.wfile.write(json.dumps({"status": "ok", "queued": len(emails)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default stderr logging
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info(f"Webhook server listening on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.server_close()


if __name__ == "__main__":
    main()
