#!/usr/bin/env python3
"""
TalentFinder — Get Telegram Chat ID
====================================
After Riz messages the bot, run this to find his chat ID.
Add the chat ID to .env as TELEGRAM_CHAT_ID.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.telegram_client import get_updates


def main():
    print("Fetching recent messages sent to the bot...")
    print("(Make sure Riz has sent at least one message to the bot first)")
    print()

    updates = get_updates()

    if not updates:
        print("No messages found. Ask Riz to send any message to the bot first.")
        return

    seen = set()
    for update in updates:
        msg = update.get("message", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        first_name = chat.get("first_name", "")
        last_name = chat.get("last_name", "")
        username = chat.get("username", "")

        if chat_id and chat_id not in seen:
            seen.add(chat_id)
            print(f"  Chat ID:  {chat_id}")
            print(f"  Name:     {first_name} {last_name}".strip())
            if username:
                print(f"  Username: @{username}")
            print()

    if seen:
        print("Copy the Chat ID above and add it to your .env file:")
        print("  TELEGRAM_CHAT_ID=<the number above>")
    else:
        print("No chat IDs found. Ask Riz to message the bot and try again.")


if __name__ == "__main__":
    main()
