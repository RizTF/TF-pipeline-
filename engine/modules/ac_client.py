"""
ActiveCampaign client — suppress contacts and manage tags.
"""

import logging
import requests
from config.settings import AC_API_URL, AC_API_KEY

logger = logging.getLogger("tf.ac")

HEADERS = {}
if AC_API_KEY:
    HEADERS = {"Api-Token": AC_API_KEY, "Content-Type": "application/json"}


def _api(method: str, endpoint: str, json_data: dict = None) -> dict:
    """Make an ActiveCampaign API request."""
    if not AC_API_URL or not AC_API_KEY:
        logger.warning("ActiveCampaign not configured — skipping")
        return {}

    url = f"{AC_API_URL}/api/3/{endpoint}"
    try:
        resp = requests.request(
            method, url, headers=HEADERS, json=json_data, timeout=15
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"AC API error ({method} {endpoint}): {e}")
        return {}


def find_contact_by_email(email_addr: str) -> dict:
    """Find a contact by email. Returns contact dict or empty."""
    data = _api("GET", f"contacts?email={email_addr}")
    contacts = data.get("contacts", [])
    return contacts[0] if contacts else {}


def add_tag_to_contact(contact_id: str, tag_name: str) -> bool:
    """Add a tag to a contact. Creates the tag if it doesn't exist."""
    if not contact_id:
        return False

    # Find or create tag
    tags_data = _api("GET", f"tags?search={tag_name}")
    tags = tags_data.get("tags", [])

    if tags:
        tag_id = tags[0]["id"]
    else:
        create_resp = _api("POST", "tags", {"tag": {"tag": tag_name, "tagType": "contact"}})
        tag = create_resp.get("tag", {})
        tag_id = tag.get("id")
        if not tag_id:
            return False

    # Apply tag to contact
    result = _api(
        "POST",
        "contactTags",
        {"contactTag": {"contact": contact_id, "tag": tag_id}},
    )
    return bool(result)


def suppress_contact(email_addr: str, reason: str = "") -> bool:
    """
    Suppress a contact — remove from all automations and add
    a reason tag. Does NOT delete the contact.
    """
    contact = find_contact_by_email(email_addr)
    if not contact:
        logger.info(f"Contact {email_addr} not found in AC — nothing to suppress")
        return False

    contact_id = contact["id"]

    # Remove from all automations
    automations = _api("GET", f"contacts/{contact_id}/contactAutomations")
    for ca in automations.get("contactAutomations", []):
        _api("DELETE", f"contactAutomations/{ca['id']}")

    # Tag with reason
    tag = f"suppressed:{reason}" if reason else "suppressed"
    add_tag_to_contact(contact_id, tag)

    logger.info(f"Suppressed {email_addr} in AC (reason: {reason})")
    return True


def hard_unsubscribe(email_addr: str) -> bool:
    """Permanently unsubscribe a contact from all lists."""
    contact = find_contact_by_email(email_addr)
    if not contact:
        return False

    contact_id = contact["id"]

    # Update contact status to unsubscribed (status 2)
    _api(
        "PUT",
        f"contacts/{contact_id}",
        {"contact": {"status": 2}},  # 2 = unsubscribed
    )

    add_tag_to_contact(contact_id, "hard-unsubscribe")

    # Remove from all automations
    automations = _api("GET", f"contacts/{contact_id}/contactAutomations")
    for ca in automations.get("contactAutomations", []):
        _api("DELETE", f"contactAutomations/{ca['id']}")

    logger.info(f"Hard unsubscribed {email_addr} from AC")
    return True


def test_connection() -> bool:
    """Quick test that the API key is valid."""
    if not AC_API_URL or not AC_API_KEY:
        return False
    data = _api("GET", "tags?limit=1")
    return "tags" in data
