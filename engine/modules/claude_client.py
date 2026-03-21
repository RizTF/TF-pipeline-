"""
Claude API client — classifies inbound emails and generates replies.
"""

import json
import logging
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CALENDLY_LINK

logger = logging.getLogger("tf.claude")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Classification prompt ────────────────────────────────────────────

CLASSIFY_SYSTEM = """You are an email classifier for TalentFinder, a UK recruitment agency.
You classify inbound replies to outreach emails sent by Paul from paul@talentfinderuk.co.uk.

Classify each email into EXACTLY ONE of these categories:

POSITIVE — The sender wants more information, is interested, or wants to book a call.
QUESTION — The sender is asking about fees, process, guarantees, timelines, or similar.
COMPLEX — The sender has a nuanced request that needs human judgement (e.g. complaints, specific negotiations, referrals to someone else internally).
NOT_INTERESTED — The sender clearly declines, says no thanks, or asks to stop contact.
UNSUBSCRIBE — The sender explicitly asks to be removed from mailing lists or says "unsubscribe".
WRONG_PERSON — The sender says they are not the right contact or have left the company.
BOOKING_CONFIRMED — This is a Calendly booking confirmation or meeting acceptance.
AUTO_REPLY — This is an automatic out-of-office reply, a bounce notification, or a delivery failure.

Return ONLY valid JSON with these fields:
{
  "category": "POSITIVE|QUESTION|COMPLEX|NOT_INTERESTED|UNSUBSCRIBE|WRONG_PERSON|BOOKING_CONFIRMED|AUTO_REPLY",
  "confidence": 0.0-1.0,
  "sender_name": "extracted name or empty string",
  "sender_company": "extracted company or empty string",
  "summary": "one-line summary of what the sender wants",
  "urgency": "HIGH|MEDIUM|LOW"
}"""

# ── Reply generation prompt ──────────────────────────────────────────

REPLY_SYSTEM = """You are Paul from TalentFinder, a UK recruitment agency. You write warm, professional, concise email replies.

Rules:
- Sign off as "Paul" (never "Paul from TalentFinder" or "The TalentFinder Team")
- Keep replies under 150 words
- Be warm but professional — no corporate waffle
- Never reference ISO 27001 — TalentFinder does not hold this certification
- For booking requests, include the Calendly link: {calendly_link}
- For fee questions: TalentFinder charges 15-20% of first-year salary depending on role complexity, with a rebate guarantee
- For process questions: Explain that TalentFinder uses a combination of headhunting, database search, and targeted advertising, with shortlists typically delivered within 5-7 working days
- For guarantee questions: TalentFinder offers a free replacement within the first 3 months if a placement doesn't work out
- Never make promises about specific candidates or timelines beyond the above
- Match the tone of the original sender — more formal if they're formal, more casual if they're casual
""".format(calendly_link=CALENDLY_LINK)

# ── Pre-call brief prompt ────────────────────────────────────────────

BRIEF_SYSTEM = """You are preparing a pre-call brief for Paul at TalentFinder before a recruitment discovery call.
Based on the email thread provided, create a concise brief with:
1. Contact name and company
2. What they're hiring for (if mentioned)
3. Key points from the email exchange
4. Suggested talking points for the call
5. Any red flags or things to be aware of

Keep it under 200 words. Use bullet points. Be direct."""


def classify_email(from_addr: str, subject: str, body: str) -> dict:
    """
    Classify an inbound email. Returns dict with category, confidence, etc.
    """
    user_msg = f"From: {from_addr}\nSubject: {subject}\n\n{body}"

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        return {
            "category": "COMPLEX",
            "confidence": 0.0,
            "sender_name": "",
            "sender_company": "",
            "summary": "Classification failed — needs manual review",
            "urgency": "MEDIUM",
        }
    except Exception as e:
        logger.error(f"Claude API error during classification: {e}")
        return {
            "category": "COMPLEX",
            "confidence": 0.0,
            "sender_name": "",
            "sender_company": "",
            "summary": f"API error: {e}",
            "urgency": "HIGH",
        }


def generate_reply(from_addr: str, subject: str, body: str, category: str) -> str:
    """
    Generate an appropriate reply for the given email category.
    Returns the reply text.
    """
    user_msg = (
        f"Category: {category}\n"
        f"From: {from_addr}\n"
        f"Subject: {subject}\n\n"
        f"{body}\n\n"
        f"Write a reply from Paul."
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=REPLY_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude API error generating reply: {e}")
        return ""


def generate_draft(from_addr: str, subject: str, body: str, summary: str) -> str:
    """
    Generate a draft reply for COMPLEX emails that Riz must approve.
    """
    user_msg = (
        f"This email was classified as COMPLEX and needs careful handling.\n"
        f"Summary: {summary}\n\n"
        f"From: {from_addr}\n"
        f"Subject: {subject}\n\n"
        f"{body}\n\n"
        f"Write a thoughtful draft reply from Paul. Riz will review before sending."
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=REPLY_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude API error generating draft: {e}")
        return ""


def generate_precall_brief(from_addr: str, subject: str, body: str) -> str:
    """
    Generate a pre-call brief when a Calendly booking is confirmed.
    """
    user_msg = (
        f"From: {from_addr}\n"
        f"Subject: {subject}\n\n"
        f"{body}"
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            system=BRIEF_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude API error generating brief: {e}")
        return ""
