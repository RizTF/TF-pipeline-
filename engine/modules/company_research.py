"""
Company research — fetches real-time info about a sender's company
to personalise objection handling and increase conversions.

Uses web search to find recent news, job postings, company size, etc.
"""

import logging
import re
import requests

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from anthropic import Anthropic

logger = logging.getLogger("tf.research")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _extract_domain(email: str) -> str:
    """Extract domain from email, skip generic providers."""
    generic = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "aol.com", "icloud.com", "live.com", "btinternet.com",
        "sky.com", "virginmedia.com", "talktalk.net", "mail.com",
    }
    match = re.search(r"@(.+)$", email.strip())
    if not match:
        return ""
    domain = match.group(1).lower()
    return "" if domain in generic else domain


def _search_company_info(company_name: str, domain: str) -> str:
    """Search for company info using web sources."""
    info_parts = []

    # Try to fetch the company website
    if domain:
        for url in [f"https://www.{domain}", f"https://{domain}"]:
            try:
                resp = requests.get(url, timeout=8, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; TalentFinder/1.0)"
                })
                if resp.status_code == 200:
                    # Extract text content (rough — just get visible text)
                    text = re.sub(r'<[^>]+>', ' ', resp.text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    info_parts.append(f"Website content ({domain}):\n{text[:3000]}")
                    break
            except Exception:
                continue

    return "\n\n".join(info_parts) if info_parts else ""


def research_company(sender_email: str, sender_name: str, sender_company: str) -> str:
    """
    Research a company and return a summary useful for objection handling.
    Returns a concise research brief or empty string if nothing found.
    """
    domain = _extract_domain(sender_email)

    if not domain and not sender_company:
        return ""

    # Gather raw info
    raw_info = _search_company_info(sender_company or domain, domain)

    if not raw_info:
        # If we can't fetch the website, use what we know
        if sender_company:
            raw_info = f"Company name: {sender_company}\nDomain: {domain or 'unknown'}"
        else:
            return ""

    # Use Claude to summarise into actionable sales intelligence
    try:
        prompt = f"""Based on the following information about a company, create a brief sales intelligence summary for a recruitment company (TalentFinder) trying to win their business.

Company: {sender_company or domain}
Contact: {sender_name}
Email domain: {domain or 'unknown'}

Raw information:
{raw_info[:4000]}

Provide a concise summary (under 200 words) with:
1. What the company does
2. Approximate size/sector
3. Any current job openings or growth signals
4. Pain points this type of company typically has with recruitment
5. A personalised angle TalentFinder could use to win them over

Be factual — only include what you can verify from the info above. If info is limited, say so briefly."""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Company research failed: {e}")
        return ""
