# TF-Pipeline Handover Document
## Date: 28 March 2026

---

## PART 1: What's Been Built (Inbound Reply Engine)

### Overview
A fully automated email processing pipeline that handles inbound replies to Paul's outreach emails. Runs on VPS (204.168.162.1) alongside the existing Scout bot.

### Architecture
```
Paul's Outlook Inbox
        ↓
Power Automate (forwards emails via HTTP POST)
        ↓
Webhook Server (port 5111 on VPS)
        ↓
incoming_emails.json (queue)
        ↓
inbox_watcher.py (runs every 2 mins via cron)
        ↓
Claude AI classifies into 8 categories
        ↓
Auto-reply / Draft / Suppress / Log
        ↓
Telegram notifications to Riz
```

### VPS Details
- **IP:** 204.168.162.1
- **SSH:** `ssh root@204.168.162.1` / Password: `C3Nv7ejgv7TU`
- **App directory:** `/home/talentfinder/app/`
- **Python venv:** `/home/talentfinder/app/venv/`
- **Scout bot:** `/home/scout/` (separate system, don't touch)

### Files on VPS (`/home/talentfinder/app/`)
```
├── .env                          # All credentials
├── inbox_watcher.py              # Main pipeline — classifies + acts on emails
├── telegram_handler.py           # Processes SEND/EDIT/SKIP commands from Telegram
├── webhook_server.py             # HTTP server on port 5111, receives emails
├── config/
│   └── settings.py               # All config loaded from .env
├── modules/
│   ├── claude_client.py          # All Claude prompts + API calls
│   ├── conversation_store.py     # Email threading — stores history per sender
│   ├── company_research.py       # Real-time company research for objection handling
│   ├── imap_client.py            # Reads webhook queue + sends via SMTP
│   ├── telegram_client.py        # Telegram notifications
│   ├── sheets_client.py          # Google Sheets logging (calls sheets_bridge.js)
│   ├── sheets_bridge.js          # Node.js bridge for Google Sheets (workaround)
│   └── ac_client.py              # ActiveCampaign — suppress/unsubscribe contacts
├── scripts/
│   ├── test_connections.py       # Tests all 7 service connections
│   ├── health_report.sh          # Sends health status to Telegram every 2 hours
│   ├── deploy.sh                 # Deployment script
│   └── setup.sh                  # Initial setup script
├── data/
│   ├── incoming_emails.json      # Webhook email queue
│   ├── conversations.json        # Conversation history per sender
│   ├── pending_drafts.json       # Drafts awaiting Riz's approval
│   ├── processed_uids.json       # Processed email tracking
│   └── telegram_offset.txt       # Telegram update offset
└── logs/
    └── inbox_watcher.log         # Processing logs
```

### Email Classification Categories
| Category | Action |
|----------|--------|
| POSITIVE | Auto-reply + suppress AC + notify Riz |
| QUESTION | Auto-reply with pricing/process info + notify Riz |
| COMPLEX | Draft for Riz approval via Telegram |
| NOT_INTERESTED | Company research → personalised objection draft for Riz approval |
| UNSUBSCRIBE | Hard unsubscribe from AC |
| WRONG_PERSON | Suppress + tag in AC |
| BOOKING_CONFIRMED | Pre-call brief sent to Riz |
| AUTO_REPLY | Silently ignored |

### Telegram Commands (Riz sends these to the bot)
- `SEND draft_1` — Send the draft as-is
- `EDIT draft_1 Your replacement text here` — Replace draft body and send
- `SKIP draft_1` — Discard the draft

### Key Features
1. **Conversation Threading** — Stores all emails per sender in `conversations.json`. Claude sees full history when generating replies, so responses are contextually aware across multiple exchanges.
2. **Smart Objection Handling** — NOT_INTERESTED emails trigger real-time company website research. Claude uses that research + conversation history to craft a personalised objection-handling reply. Created as a draft for Riz's approval (not auto-sent). If someone has declined twice, sends a graceful goodbye.
3. **Draft Editing** — Riz can modify any draft before sending via the EDIT command.
4. **Health Reports** — Telegram status update every 2 hours (webhook status, queue size, last run time).

### Services & Credentials (.env)
| Service | Status | Notes |
|---------|--------|-------|
| Anthropic (Claude) | Working | claude-sonnet-4-20250514 |
| SMTP (Outlook) | Working | paul@talentfinderuk.co.uk / basic auth |
| Telegram | Working | Bot token + chat ID 1703019894 |
| ActiveCampaign | Working | API key in .env |
| Google Sheets | Working | Via Node.js bridge using Scout's service account |
| Webhook Server | Working | systemd service `tf-webhook` on port 5111 |
| Power Automate | Working | 90-day trial (HTTP Premium connector) |

### Cron Jobs (`/etc/cron.d/`)
- `talentfinder-engine` — Runs `inbox_watcher.py` and `telegram_handler.py` every 2 minutes
- `tf-health-report` — Runs `health_report.sh` every 2 hours

### Known Limitations
- **Power Automate trial** — HTTP Premium connector on 90-day trial, needs permanent solution
- **No retry on webhook** — If VPS is down when Power Automate sends, email is lost
- **Google Sheets auth** — Python can't parse the service account key directly, uses Node.js bridge workaround
- **M365 blocks IMAP/EWS** — That's why we use Power Automate for receiving and SMTP for sending

---

## PART 2: ActiveCampaign Personalised Outreach Project

### Objective
Build a system that creates personalised cold outreach emails at scale using Claude AI, sent via ActiveCampaign automations.

### Strategy

#### Phase 1: Research & Draft
1. **Pull contacts from AC** — Batch export contacts with name, email, company, role, any existing tags
2. **Research each company** — Use the company_research.py module (already built) to scrape their website and extract:
   - What the company does
   - Sector and approximate size
   - Current job openings (growth signals)
   - Pain points relevant to recruitment
3. **Claude drafts personalised email** — Not mail merge ("Hi {name}") but genuinely unique content per company:
   - References what their business actually does
   - Identifies a relevant recruitment angle
   - Matches the right TalentFinder pricing tier to their likely salary range
   - Warm, conversational tone matching Paul's style
4. **Store draft in AC** — Save the personalised email body as a custom field on the contact

#### Phase 2: Send via AC Automation
1. **AC automation triggers** on contacts with a populated custom email field
2. **Sends the personalised email** from paul@talentfinderuk.co.uk
3. **Tracks opens/clicks** via AC's built-in analytics
4. **Tags contacts** based on engagement (opened, clicked, replied)

#### Phase 3: Follow-Up Sequences
1. If no reply after X days → Claude drafts a follow-up (referencing the original email)
2. If opened but no reply → Different follow-up angle
3. If replied → Feeds into the existing inbound reply engine (Part 1)

### Suggested Architecture (New Session)
```
ActiveCampaign (contact lists)
        ↓ (MCP via Chrome / AC API)
Pull contacts in batches
        ↓
Company research (scrape website)
        ↓
Claude drafts personalised email
        ↓
Push personalised email back to AC (custom field)
        ↓
AC automation sends the email
        ↓
Replies land in Paul's inbox
        ↓
Power Automate → Webhook → Existing inbound engine
```

### MCP / Chrome Integration
The new session will use MCP to access ActiveCampaign via Chrome browser, which allows:
- Direct interaction with AC's UI for contact management
- Viewing contact details, lists, and segments
- Setting up automations visually
- No need to build complex API integrations from scratch

### API Cost Estimate (Claude)
| Volume | Research + Draft Cost |
|--------|----------------------|
| 100 emails/day | ~£0.80/day |
| 500 emails/day | ~£4/day |
| 1,000 emails/day | ~£8/day |
| 10,000 emails/month | ~£80/month |

Based on Claude Sonnet at ~$3/M input + $15/M output tokens. Each email needs ~1,000 input tokens (company research + prompt) and ~200 output tokens (email draft).

### TalentFinder Business Info for Email Prompts
This is critical — all outreach must use correct information:

**What TalentFinder Is:**
- UK's #1 guaranteed fixed-fee recruitment service
- Fixed fee — NO commission, NO percentage of salary, NO hidden costs
- Guaranteed hire — dedicated recruiter works until the role is filled
- Average fill time: 6 weeks
- Trusted by 23,000+ employers across 76+ cities
- Uses headhunting, database search, and targeted advertising
- Based in Preston, Lancashire — covers all UK and Ireland
- Phone: 01772 886799 | WhatsApp: +447827918987

**UK Pricing (+ VAT):**
- Standard: £1,500 — roles under £30k
- Professional: £2,000 — roles £30k-£44,999
- Senior: £3,000 — roles £45k-£59,999
- Executive: £4,000 — roles £60k+

**Ireland Pricing (NO VAT):**
- Standard: €1,800 — roles under €30k
- Professional: €2,300 — roles €30k-€44k
- Senior: €3,300 — roles €45k-€59k
- Executive: €4,300 — roles €60k+
- Replacement Add-On: €950

**100% Refund Guarantee:**
- This is an OPTIONAL add-on (additional insurance purchase)
- NOT included as standard — do NOT say it's included
- £750 + VAT for the £1,500 package
- £1,000 + VAT for all other packages
- Provides 12-month replacement guarantee if employment terminated for any reason

**Key Selling Points vs Commission Agencies:**
- A £40k role at 20% commission = £8,000. TalentFinder = £2,000. Saves £6,000.
- A £60k role at 20% commission = £12,000. TalentFinder = £4,000. Saves £8,000.
- No risk — guaranteed hire means we work until it's filled
- No lock-in contracts

### Existing Modules That Can Be Reused
- `company_research.py` — Already built for objection handling, can be reused for outreach research
- `ac_client.py` — Already has AC API integration for finding/tagging contacts
- `claude_client.py` — Prompt structure can be adapted for outreach drafting

### Paul's Outreach Style
- Warm, conversational, not corporate
- Short emails (under 150 words)
- Signs off as "Paul"
- Never pushy — consultative approach
- References specific things about the recipient's company
- Ends with a soft CTA (Calendly link or "happy to have a quick chat")

### Calendly Link
`https://calendly.com/talent-finder/recruitment-clone`

---

## PART 3: Git Repository

- **Repo:** github.com/RizTF/TF-pipeline-
- **Branch:** `claude/enhance-tfpipeline-site-PY81w`
- **Latest commit:** Conversation threading, draft editing, smart objection handling

---

## PART 4: Quick Reference

### SSH into VPS
```bash
ssh root@204.168.162.1
# Password: C3Nv7ejgv7TU
```

### Check status on VPS
```bash
source /home/talentfinder/app/venv/bin/activate
cd /home/talentfinder/app
python3 scripts/test_connections.py
```

### View logs
```bash
tail -50 /home/talentfinder/app/logs/inbox_watcher.log
```

### Restart webhook server
```bash
systemctl restart tf-webhook
```

### Check cron jobs
```bash
cat /etc/cron.d/talentfinder-engine
cat /etc/cron.d/tf-health-report
```

### Tenant ID (Microsoft/Azure)
`148ba1ce-d2df-4456-9896-f97916cc687d`
