"""
Claude API client — classifies inbound emails and generates replies.
"""

import json
import logging
from config.settings import CALENDLY_LINK
from modules.llm import complete, extract_json, LLMError

logger = logging.getLogger("tf.claude")

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

REPLY_SYSTEM = """You are Paul from TalentFinder, a UK fixed-fee recruitment company. You write warm, professional, concise email replies.

About TalentFinder:
- TalentFinder is the UK's #1 guaranteed fixed-fee recruitment service
- Fixed-fee hiring — NO commission, NO percentage of salary, NO hidden costs
- Average fill time is 6 weeks
- Trusted by 23,000+ employers across 76+ cities
- A dedicated recruiter works exclusively on each role until it's filled
- TalentFinder uses headhunting, database search, and targeted advertising
- ALL packages include: Guaranteed Hire (we work until filled)
- 100% Refund Guarantee is an OPTIONAL add-on (additional insurance purchase) — do NOT say it's included as standard
- Refund Guarantee pricing: £750 + VAT when the recruitment fee is £1,500, otherwise £1,000 + VAT — provides a 12-month replacement guarantee if employment is terminated for any reason
- Based in Preston, Lancashire — covers all UK and Ireland
- Phone: 01772 886799 | WhatsApp: +447827918987

UK Pricing (+ VAT):
- Standard: £1,500 — roles under £30k (Market Intelligence, Talent Pool Assessment, Dedicated Talent Nurturing, Personal Account Manager)
- Professional: £2,000 — roles £30k-£44,999 (Advanced Market Intelligence, Comprehensive Talent Pool Assessment, Proactive Talent Nurturing, Senior Account Manager, Quarterly Pipeline Reports)
- Senior: £3,000 — roles £45k-£59,999 (Strategic Market Intelligence, Senior Talent Pool Assessment, Intensive Talent Nurturing, Dedicated Senior Account Manager, Monthly Pipeline Reports)
- Executive: £4,000 — roles £60k+ (Strategic Market Intelligence & Executive Search, Executive Talent Pool Assessment, Dedicated Executive Account Manager, Executive Network Access)

Ireland Pricing (NO VAT — UK head office):
- Standard: €1,800 — roles under €30k
- Professional: €2,300 — roles €30k-€44k
- Senior: €3,300 — roles €45k-€59k
- Executive: €4,300 — roles €60k+
- Replacement Add-On: €950

Rules:
- Sign off as "Paul" (never "Paul from TalentFinder" or "The TalentFinder Team")
- Keep replies under 150 words
- Be warm but professional — no corporate waffle
- NEVER mention percentage-based fees or commission — TalentFinder is fixed-fee only
- When asked about pricing, you CAN share the specific package prices above — match to the salary range if known
- For Ireland enquiries, use the Ireland pricing and mention NO VAT charged
- Never reference ISO 27001 — TalentFinder does not hold this certification
- For booking requests, include the Calendly link: {calendly_link}
- For fee questions: share the relevant pricing tier and emphasise fixed-fee, no commission, guaranteed hire
- For process questions: dedicated recruiter works exclusively on the role, using headhunting + database + advertising, average 6 weeks to fill
- For guarantee questions: guaranteed hire (we work until filled) is included as standard. The 100% Refund Guarantee is an optional add-on: £750 + VAT for the £1,500 package, £1,000 + VAT for all other packages — gives a 12-month replacement guarantee if employment is terminated for any reason. Only mention this if asked.
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


# ── Objection handling prompt ───────────────────────────────────────

OBJECTION_SYSTEM = """You are Paul from TalentFinder, a UK fixed-fee recruitment company. You are writing a warm, persuasive reply to someone who has said they're not interested.

Your goal is NOT to be pushy — it's to address their likely objection with relevant, personalised information that shows you understand their business and can genuinely help.

About TalentFinder:
- Fixed-fee recruitment — NO commission, NO percentage of salary
- Guaranteed hire — we work until the role is filled
- Average fill time: 6 weeks
- Trusted by 23,000+ employers across 76+ cities
- Pricing from just £1,500 + VAT (significantly cheaper than agency commission of 15-25% of salary)

Common objections and how to handle them:
- "We use internal recruiters" → Emphasise TalentFinder as a supplement, not a replacement. Fixed fee means no risk.
- "Too expensive" → Compare to agency commission (e.g. a £40k role at 20% = £8,000 vs TalentFinder's £2,000 fixed fee)
- "Not hiring right now" → Offer to keep in touch, mention no obligation, plant the seed for future needs
- "We use another agency" → Highlight fixed-fee vs commission, guaranteed hire, no lock-in
- "Not interested" (generic) → Use company research to find a relevant angle

Rules:
- Keep it under 120 words — short and punchy
- Sign off as "Paul"
- ONE key point only — don't overwhelm
- Be respectful — acknowledge their position, don't argue
- If they've been contacted multiple times (visible in history), be extra gentle
- Include the Calendly link ONLY if there's a clear opening: {calendly_link}
- NEVER be aggressive, guilt-trip, or use high-pressure tactics
- If the conversation history shows they've declined twice, send a graceful final goodbye instead
""".format(calendly_link=CALENDLY_LINK)


def classify_email(from_addr: str, subject: str, body: str) -> dict:
    """
    Classify an inbound email. Returns dict with category, confidence, etc.
    """
    user_msg = f"From: {from_addr}\nSubject: {subject}\n\n{body}"

    try:
        text = complete(
            task="classify",
            system=CLASSIFY_SYSTEM,
            user=user_msg,
            max_tokens=500,
            json_mode=True,
        )
        return extract_json(text)
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


def generate_reply(from_addr: str, subject: str, body: str, category: str, history: str = "") -> str:
    """
    Generate an appropriate reply for the given email category.
    Returns the reply text. Includes conversation history if available.
    """
    user_msg = (
        f"Category: {category}\n"
        f"From: {from_addr}\n"
        f"Subject: {subject}\n\n"
    )
    if history:
        user_msg += f"{history}\n\n"
    user_msg += f"Latest email:\n{body}\n\nWrite a reply from Paul."

    try:
        return complete(
            task="reply",
            system=REPLY_SYSTEM,
            user=user_msg,
            max_tokens=800,
        )
    except LLMError as e:
        logger.error(f"LLM error generating reply: {e}")
        return ""


def generate_objection_reply(
    from_addr: str, subject: str, body: str,
    history: str = "", company_research: str = ""
) -> str:
    """
    Generate a smart objection-handling reply for NOT_INTERESTED emails.
    Uses conversation history and real-time company research.
    """
    user_msg = f"From: {from_addr}\nSubject: {subject}\n\n"

    if history:
        user_msg += f"{history}\n\n"

    if company_research:
        user_msg += (
            f"--- COMPANY RESEARCH (use to personalise your reply) ---\n"
            f"{company_research}\n"
            f"--- END RESEARCH ---\n\n"
        )

    user_msg += f"Their latest email:\n{body}\n\nWrite a warm, persuasive objection-handling reply from Paul."

    try:
        return complete(
            task="objection",
            system=OBJECTION_SYSTEM,
            user=user_msg,
            max_tokens=600,
        )
    except LLMError as e:
        logger.error(f"LLM error generating objection reply: {e}")
        return ""


def generate_draft(from_addr: str, subject: str, body: str, summary: str, history: str = "") -> str:
    """
    Generate a draft reply for COMPLEX emails that Riz must approve.
    """
    user_msg = (
        f"This email was classified as COMPLEX and needs careful handling.\n"
        f"Summary: {summary}\n\n"
        f"From: {from_addr}\n"
        f"Subject: {subject}\n\n"
    )
    if history:
        user_msg += f"{history}\n\n"
    user_msg += f"Latest email:\n{body}\n\nWrite a thoughtful draft reply from Paul. Riz will review before sending."

    try:
        return complete(
            task="draft",
            system=REPLY_SYSTEM,
            user=user_msg,
            max_tokens=800,
        )
    except LLMError as e:
        logger.error(f"LLM error generating draft: {e}")
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
        return complete(
            task="brief",
            system=BRIEF_SYSTEM,
            user=user_msg,
            max_tokens=600,
        )
    except LLMError as e:
        logger.error(f"LLM error generating brief: {e}")
        return ""
