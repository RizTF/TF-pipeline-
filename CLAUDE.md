# CLAUDE.md — TalentFinder AI Email Responder

> This file is automatically loaded by Claude Code at the start of every session.
> It contains all knowledge about the TF-Pipeline inbound reply engine.

---

## Project Overview

**TF-Pipeline** is an AI-powered email reply engine that automatically handles inbound replies to Paul's recruitment outreach emails. It classifies emails, auto-replies, creates drafts for review, and manages ActiveCampaign contacts — all controlled via Telegram from Riz's iPhone.

**Repo:** github.com/RizTF/TF-pipeline-
**Branch:** claude/enhance-tfpipeline-site-PY81w
**VPS:** 204.168.162.1 (SSH: root / C3Nv7ejgv7TU)
**App directory on VPS:** /home/talentfinder/app/
**Scout bot (separate):** /home/scout/ — do NOT modify

---

## TalentFinder Business Information

### What TalentFinder Is
- UK's #1 guaranteed fixed-fee recruitment service
- Fixed fee — NO commission, NO percentage of salary, NO hidden costs
- Guaranteed hire — a dedicated recruiter works exclusively on each role until it's filled
- Average fill time: 6 weeks
- Trusted by 23,000+ employers across 76+ cities
- Uses headhunting, database search, and targeted advertising
- Based in Preston, Lancashire — covers all UK and Ireland
- Phone: 01772 886799 | WhatsApp: +447827918987
- Website: talentfinderco.co.uk (guaranteed recruitment) / talentfinderuk.co.uk (advertising packages)
- Calendly: https://calendly.com/talent-finder/recruitment-clone

### UK Pricing (all + VAT)
| Tier | Price | Salary Range | Includes |
|------|-------|-------------|----------|
| Standard | £1,500 | Under £30k | Market Intelligence, Talent Pool Assessment, Dedicated Talent Nurturing, Personal Account Manager |
| Professional | £2,000 | £30k-£44,999 | Advanced Market Intelligence, Comprehensive Talent Pool Assessment, Proactive Talent Nurturing, Senior Account Manager, Quarterly Pipeline Reports |
| Senior | £3,000 | £45k-£59,999 | Strategic Market Intelligence, Senior Talent Pool Assessment, Intensive Talent Nurturing, Dedicated Senior Account Manager, Monthly Pipeline Reports |
| Executive | £4,000 | £60k+ | Strategic Market Intelligence & Executive Search, Executive Talent Pool Assessment, Dedicated Executive Account Manager, Executive Network Access |

### Ireland Pricing (NO VAT — UK head office)
| Tier | Price | Salary Range |
|------|-------|-------------|
| Standard | €1,800 | Under €30k |
| Professional | €2,300 | €30k-€44k |
| Senior | €3,300 | €45k-€59k |
| Executive | €4,300 | €60k+ |
| Replacement Add-On | €950 | — |

### 100% Refund Guarantee — IMPORTANT
- **THIS IS AN OPTIONAL ADD-ON** — it is NOT included as standard
- It is an additional insurance purchase the client can opt into
- £750 + VAT when the recruitment fee is £1,500
- £1,000 + VAT for all other packages
- Provides a 12-month replacement guarantee if employment is terminated for any reason
- **NEVER say the refund guarantee is included as standard**
- Only mention it if the prospect specifically asks about guarantees/refunds

### Key Selling Points vs Commission Agencies
- A £40k role at 20% commission = £8,000. TalentFinder = £2,000. **Saves £6,000**
- A £60k role at 20% commission = £12,000. TalentFinder = £4,000. **Saves £8,000**
- No risk — guaranteed hire means we work until it's filled
- No lock-in contracts
- No percentage of salary — completely fixed fee

### Things to NEVER Say
- Never mention percentage-based fees or commission — TalentFinder is fixed-fee only
- Never reference ISO 27001 — TalentFinder does not hold this certification
- Never say the refund guarantee is included as standard
- Never promise specific candidates or specific timelines
- Never say "Paul from TalentFinder" or "The TalentFinder Team" — just "Paul"

### Paul's Email Style
- Warm, conversational, not corporate
- Short emails (under 150 words)
- Signs off as "Paul" only
- Never pushy — consultative approach
- References specific things about the recipient's company
- Ends with a soft CTA (Calendly link or "happy to have a quick chat")
- Matches the tone of the sender — formal if they're formal, casual if casual

---

## System Architecture

```
Paul's Outlook Inbox (paul@talentfinderuk.co.uk)
        ↓
Power Automate (HTTP Premium — 90-day trial)
  forwards every inbound email via HTTP POST
        ↓
Webhook Server (port 5111, systemd: tf-webhook)
  POST /incoming → queues to incoming_emails.json
  GET /health → returns status
        ↓
inbox_watcher.py (cron every 2 mins)
  reads queue → Claude classifies → takes action
        ↓
Actions: auto-reply / draft / suppress AC / log Sheets / notify Telegram
        ↓
telegram_handler.py (cron every 2 mins)
  reads Riz's commands → processes drafts and system commands
```

### Why This Architecture
- M365 blocks IMAP basic auth AND EWS AND IMAP OAuth on paul@talentfinderuk.co.uk
- SMTP basic auth still works for sending
- Power Automate with HTTP Premium connector (90-day trial) is the workaround for receiving
- Google Sheets: Python's google-auth can't parse the service account key, so we use a Node.js bridge (sheets_bridge.js) that calls Scout's working credentials

---

## Email Classification (8 Categories)

| Category | Action | Auto-sent? |
|----------|--------|-----------|
| POSITIVE | Auto-reply + suppress AC + notify Riz | Yes |
| QUESTION | Auto-reply with pricing/process info + notify Riz | Yes |
| COMPLEX | Draft created → Riz reviews via Telegram | No — needs approval |
| NOT_INTERESTED | Company researched → personalised objection draft → Riz approves | No — needs approval |
| UNSUBSCRIBE | Hard unsubscribe from ActiveCampaign | N/A |
| WRONG_PERSON | Suppress + tag in AC | N/A |
| BOOKING_CONFIRMED | Pre-call brief generated and sent to Riz | N/A |
| AUTO_REPLY | Silently ignored (out-of-office, bounces) | N/A |

---

## Key Features

### Conversation Threading
- `data/conversations.json` stores last 10 exchanges per sender email
- Every inbound and outbound email is recorded
- Full history passed to Claude when generating any reply
- Ensures Claude doesn't repeat itself or contradict earlier messages

### Smart Objection Handling (NOT_INTERESTED)
1. `company_research.py` extracts domain from sender email
2. Fetches their company website, strips HTML to text
3. Claude summarises into sales intelligence
4. `generate_objection_reply()` crafts a personalised, non-pushy reply (under 120 words)
5. Created as a **draft** — not auto-sent
6. If conversation history shows 2 previous declines → graceful goodbye instead

### Two-Way Telegram Control
Riz can control everything from iPhone via Telegram:

**Draft commands:**
- `SEND draft_1` — Send as-is
- `EDIT draft_1 your replacement text` — Replace body and send
- `SKIP draft_1` — Discard
- `DRAFTS` — List all pending drafts

**System commands:**
- `STATUS` — Health overview (webhook, queue, drafts, pause state)
- `LOGS` / `LOGS 20` — Recent log entries
- `QUEUE` — Show queued emails
- `STATS` — Processing statistics by category
- `HISTORY email@example.com` — Conversation history for a sender
- `TEST` — Run all 7 connection tests
- `PAUSE` — Pause email processing
- `RESUME` — Resume processing
- `HELP` — Show all commands

### Health Reports
- Telegram status update every 2 hours via cron
- Reports: webhook status, queue size, last watcher run time

---

## Files on VPS (/home/talentfinder/app/)

| File | Purpose |
|------|---------|
| .env | All credentials (Anthropic, SMTP, Telegram, AC, Sheets) |
| inbox_watcher.py | Main pipeline — reads queue, classifies with Claude, takes action |
| telegram_handler.py | Two-way Telegram control — draft commands + system commands |
| webhook_server.py | HTTP server on port 5111, receives emails from Power Automate |
| config/settings.py | Config loader from .env |
| config/google_credentials.json | Shared from Scout bot |
| modules/claude_client.py | All Claude prompts (classify, reply, objection, draft, brief) |
| modules/conversation_store.py | Email threading — stores history per sender |
| modules/company_research.py | Real-time company website scraping for objection handling |
| modules/imap_client.py | SMTP sending + webhook queue reader |
| modules/telegram_client.py | Telegram bot notifications |
| modules/sheets_client.py | Google Sheets logging (calls Node.js bridge) |
| modules/sheets_bridge.js | Node.js bridge for Sheets auth (Python can't parse key) |
| modules/ac_client.py | ActiveCampaign — suppress/unsubscribe/tag contacts |
| scripts/test_connections.py | Tests all 7 service connections |
| scripts/health_report.sh | Telegram health report (cron every 2 hours) |
| data/incoming_emails.json | Webhook email queue |
| data/conversations.json | Thread history per sender |
| data/pending_drafts.json | Drafts awaiting Riz's approval |
| data/paused.flag | Created by PAUSE command, removed by RESUME |

---

## Services & Credentials

| Service | Config | Notes |
|---------|--------|-------|
| Anthropic (Claude) | ANTHROPIC_API_KEY in .env | Model: claude-sonnet-4-20250514 |
| SMTP (Outlook) | EMAIL_ADDRESS + EMAIL_PASSWORD in .env | paul@talentfinderuk.co.uk, smtp.office365.com:587 |
| Telegram | TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env | Chat ID: 1703019894 |
| ActiveCampaign | AC_API_URL + AC_API_KEY in .env | Suppress, unsub, tag contacts |
| Google Sheets | GOOGLE_SHEETS_ID in .env | Sheet ID: 1rxo_PLiTrJYNMMkgiO_NTxdEe33ev8mCpVasw_vZBZk |
| Webhook Server | systemd: tf-webhook | Port 5111, restart: systemctl restart tf-webhook |
| Power Automate | External (M365) | 90-day trial, HTTP Premium connector |

---

## Cron Jobs (/etc/cron.d/)

| File | Schedule | Command |
|------|----------|---------|
| talentfinder-engine | Every 2 mins | inbox_watcher.py + telegram_handler.py |
| tf-health-report | Every 2 hours | health_report.sh (Telegram status) |

---

## ActiveCampaign Integration

Currently does:
- **suppress_contact(email, reason)** — Removes from all automations, tags with reason
- **hard_unsubscribe(email)** — Sets status to unsubscribed, removes from automations
- **find_contact_by_email(email)** — Lookup contact
- **add_tag_to_contact(contact_id, tag_name)** — Apply tag (creates if needed)

Tags used: `suppressed:positive-reply`, `suppressed:not-interested`, `suppressed:wrong-person`, `hard-unsubscribe`

---

## Known Limitations

1. **Power Automate 90-day trial** — HTTP Premium connector will expire, needs permanent solution
2. **No webhook retry** — If VPS is down when Power Automate sends, email is lost
3. **Google Sheets auth hack** — Python can't parse service account key, relies on Node.js bridge
4. **M365 blocks IMAP/EWS** — Cannot read inbox directly, must use Power Automate
5. **Draft expiry** — Old unapproved drafts sit in pending_drafts.json indefinitely
6. **VPS IPv6 issues** — Node.js needs --dns-result-order=ipv4first, Python needs socket.AF_INET forcing

---

## Quick VPS Commands

```bash
# SSH in
ssh root@204.168.162.1  # Password: C3Nv7ejgv7TU

# Activate venv
source /home/talentfinder/app/venv/bin/activate
cd /home/talentfinder/app

# Test all connections
python3 scripts/test_connections.py

# View logs
tail -50 logs/inbox_watcher.log

# Restart webhook
systemctl restart tf-webhook

# Check crons
cat /etc/cron.d/talentfinder-engine

# Check drafts
cat data/pending_drafts.json

# Check conversations
cat data/conversations.json

# Manual run
python3 inbox_watcher.py
```

---

## Microsoft / Azure

- Tenant ID: 148ba1ce-d2df-4456-9896-f97916cc687d
- Email: paul@talentfinderuk.co.uk
- SMTP password in .env (EMAIL_PASSWORD)
- Basic auth works for SMTP only, blocked for IMAP/EWS

---

## Future: AC Personalised Outreach Project

Planned system to generate personalised cold outreach at scale:
1. Pull contacts from ActiveCampaign
2. Research each company website with company_research.py
3. Claude drafts a unique personalised email per company
4. Push back to AC as custom field, AC automation sends it
5. Replies feed into this existing inbound engine

API cost estimate: ~£8/day for 1,000 emails (Claude Sonnet).
See HANDOVER.md for full strategy.

---

## Recommended Plugins

### CLI-Anything
Makes 40+ desktop apps controllable by Claude through structured CLI commands.
Supports: GIMP, Blender, OBS, LibreOffice, Audacity, browser automation, and more.

**Install in any Claude Code CLI session:**
```
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything
```

**GitHub:** github.com/HKUDS/CLI-Anything
**CLI-Hub:** https://hkuds.github.io/CLI-Anything/

### Auto Research (Karpathy-inspired)
Autonomous goal-directed iteration: Modify → Verify → Keep/Discard → Repeat.
Auto-detects what you're building and generates verifiable checklists.

**Install in any Claude Code CLI session:**
```
/plugin marketplace add uditgoenka/autoresearch
/plugin install autoresearch
```

**GitHub:** github.com/uditgoenka/autoresearch
