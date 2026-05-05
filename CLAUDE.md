# CLAUDE.md — TalentFinder AI Operating System

> This file is automatically loaded by Claude Code at the start of every session.
> It contains all knowledge about TalentFinder's AI systems across all projects.
> **Last updated: 2026-05-05**

---

## ABOUT ME & THE BUSINESS

- **Owner:** Riz, TalentFinder Ltd
- **Core business:** UK fixed-fee recruitment, two brands:
  - **talentfinderco.co.uk** = Guaranteed Hire, £1,500–£4,000 flat fee, managed service
  - **talentfinderuk.co.uk** = self-service job advertising, £399–£599
- **Team:** 6 sales staff, 4 recruiters, 1 admin, 1 business partner
- **Revenue:** ~£80k/month, costs ~£65k/month
- **Sectors:** Engineering, Finance, Legal, Construction, UK + Ireland
- **All strategies must comply with Islamic principles** — no riba, no gharar, no deception

---

## TECH STACK (CONFIRMED LIVE)

- **VPS:** Hetzner at 204.168.162.1 (SSH: root / C3Nv7ejgv7TU)
- **Automation:** Google Apps Script + n8n (port 5678, Docker container)
- **Middleware:** Google Sheets
- **CRM:** Recruit with Atlas (migrating from FiveCRM, no API — use Google Sheets mirror)
- **Cold email:** Instantly.ai — John sends all emails, 50/day cap, 30-second sleep between sends
- **LinkedIn:** HeyReach — Faruk (primary InMail), James (backup Sales Nav only)
- **Warm email:** ActiveCampaign (opted-in contacts only, never cold data)
- **Enrichment:** Prospeo
- **AI:** Claude API (claude-sonnet-4-6) for all AI features
- **Agent:** Scout at /home/scout/ (scout.js + runner.js), controlled via Telegram bot
- **Webhook server:** Python at /home/talentfinder/app/ (port 5111)
- **Booking:** Calendly (calendly.com/talent-finder/recruitment-clone for candidates, calendly.com/talent-finder/15min for BD)

---

## LIVE SYSTEMS — RING-FENCE

**NEVER touch without explicit confirmation from Riz:**

- hire@talentfinderco.co.uk and hire@talentfinderuk.co.uk email accounts
- Active Instantly campaigns (BD Outreach, UK Generic Cold Sequence etc)
- Active HeyReach LinkedIn campaigns (Faruk and James accounts)
- The master TalentFinder Google Sheet with live client/candidate data
- ActiveCampaign sequences currently running
- /home/scout/ directory and all scripts (live agent system)
- /home/scout/.env (contains live API keys for Telegram, Prospeo, Unipile, etc.)
- /home/talentfinder/ directory (webhook server, app, config, data)
- /opt/tfsales/ directory (TF Sales Talent — live system)
- Ports 8100-8199 (reserved for TF Sales Talent)
- Port 5111 (talentfinder webhook server)
- Port 5678 (n8n automation — public-facing)
- Port 3333 (tfsales node server)
- tfsales_db and talentfinder_db databases
- n8n container and its workflows
- Cron job: unipile-inmail.js runs Mon-Fri at 10:00 from /home/scout/

---

## PROJECT 1: TF-Pipeline (Inbound Reply Engine)

### Overview
AI-powered email reply engine that automatically handles inbound replies to Paul's recruitment outreach emails. Classifies emails, auto-replies, creates drafts for review, and manages ActiveCampaign contacts — all controlled via Telegram from Riz's iPhone.

**Repo:** github.com/RizTF/TF-pipeline-
**Branch:** claude/enhance-tfpipeline-site-PY81w
**App directory on VPS:** /home/talentfinder/app/
**Model:** claude-sonnet-4-20250514 (DEPRECATED — migrate to claude-sonnet-4-6)

### Architecture
```
Paul's Outlook Inbox (paul@talentfinderuk.co.uk)
        |
Power Automate (HTTP Premium — 90-day trial)
  forwards every inbound email via HTTP POST
        |
Webhook Server (port 5111, systemd: tf-webhook)
  POST /incoming -> queues to incoming_emails.json
  GET /health -> returns status
        |
inbox_watcher.py (cron every 2 mins)
  reads queue -> Claude classifies -> takes action
        |
Actions: auto-reply / draft / suppress AC / log Sheets / notify Telegram
        |
telegram_handler.py (cron every 2 mins)
  reads Riz's commands -> processes drafts and system commands
```

### Why This Architecture
- M365 blocks IMAP basic auth AND EWS AND IMAP OAuth on paul@talentfinderuk.co.uk
- SMTP basic auth still works for sending
- Power Automate with HTTP Premium connector (90-day trial) is the workaround for receiving
- Google Sheets: Python's google-auth can't parse the service account key, so we use a Node.js bridge (sheets_bridge.js) that calls Scout's working credentials

### Email Classification (8 Categories)

| Category | Action | Auto-sent? |
|----------|--------|-----------|
| POSITIVE | Auto-reply + suppress AC + notify Riz | Yes |
| QUESTION | Auto-reply with pricing/process info + notify Riz | Yes |
| COMPLEX | Draft created -> Riz reviews via Telegram | No — needs approval |
| NOT_INTERESTED | Company researched -> personalised objection draft -> Riz approves | No — needs approval |
| UNSUBSCRIBE | Hard unsubscribe from ActiveCampaign | N/A |
| WRONG_PERSON | Suppress + tag in AC | N/A |
| BOOKING_CONFIRMED | Pre-call brief generated and sent to Riz | N/A |
| AUTO_REPLY | Silently ignored (out-of-office, bounces) | N/A |

### Key Features

**Conversation Threading:**
- data/conversations.json stores last 10 exchanges per sender email
- Every inbound and outbound email is recorded
- Full history passed to Claude when generating any reply

**Smart Objection Handling (NOT_INTERESTED):**
1. company_research.py extracts domain from sender email
2. Fetches their company website, strips HTML to text
3. Claude summarises into sales intelligence
4. generate_objection_reply() crafts a personalised reply (under 120 words)
5. Created as a draft — not auto-sent
6. If 2 previous declines -> graceful goodbye instead

**Two-Way Telegram Control:**
- SEND draft_1 / EDIT draft_1 text / SKIP draft_1 / DRAFTS
- STATUS / LOGS / QUEUE / STATS / HISTORY email / TEST / PAUSE / RESUME / HELP

**Health Reports:** Telegram status update every 2 hours via cron

### Files on VPS (/home/talentfinder/app/)

| File | Purpose |
|------|---------|
| .env | All credentials (Anthropic, SMTP, Telegram, AC, Sheets) |
| inbox_watcher.py | Main pipeline — reads queue, classifies, takes action |
| telegram_handler.py | Two-way Telegram control |
| webhook_server.py | HTTP server on port 5111 |
| modules/claude_client.py | All Claude prompts (classify, reply, objection, draft, brief) |
| modules/conversation_store.py | Email threading — stores history per sender |
| modules/company_research.py | Real-time company scraping for objection handling |
| modules/imap_client.py | SMTP sending + webhook queue reader |
| modules/telegram_client.py | Telegram bot notifications |
| modules/sheets_client.py | Google Sheets logging (calls Node.js bridge) |
| modules/sheets_bridge.js | Node.js bridge for Sheets auth |
| modules/ac_client.py | ActiveCampaign — suppress/unsubscribe/tag contacts |
| scripts/test_connections.py | Tests all 7 service connections |
| scripts/health_report.sh | Telegram health report (cron every 2 hours) |
| data/incoming_emails.json | Webhook email queue |
| data/conversations.json | Thread history per sender |
| data/pending_drafts.json | Drafts awaiting Riz's approval |
| data/paused.flag | Created by PAUSE command, removed by RESUME |

### ActiveCampaign Integration
- suppress_contact(email, reason) — Removes from all automations, tags with reason
- hard_unsubscribe(email) — Sets status to unsubscribed
- find_contact_by_email(email) — Lookup contact
- add_tag_to_contact(contact_id, tag_name) — Apply tag
- Tags: suppressed:positive-reply, suppressed:not-interested, suppressed:wrong-person, hard-unsubscribe

### Known Limitations
1. Power Automate 90-day trial — HTTP Premium connector will expire
2. No webhook retry — If VPS is down, email is lost
3. Google Sheets auth hack — relies on Node.js bridge
4. M365 blocks IMAP/EWS — must use Power Automate
5. Draft expiry — old unapproved drafts sit indefinitely
6. VPS IPv6 issues — Node.js needs --dns-result-order=ipv4first

---

## PROJECT 2: TF Lead Engine (AI Appointment Setting)

### Overview
AI appointment setting service for MSPs and finance brokers. Finds intent signals, personalises outreach, and books meetings — all automated.

**Repo:** github.com/RizTF/tf-lead-engine (private)
**Branch:** feature/infra-scaffold
**VPS directory:** /opt/tflead/
**Port range:** 8200-8299
**Docker network:** tflead-network
**Database:** tflead_db (MySQL 8.0)
**Telegram bot:** @Tflead_bot (chat ID: 1703019894)
**Website:** Next.js 14 at /opt/tflead/website/ (target: Vercel, domain: tflead.co.uk pending)
**Google Sheet:** 1QwM5Abw_cDkRZtyQmQWtbvqlQJDJ_c38tJSTtBsdWEc
**Tests:** 133 passing, 84.3% coverage

### Docker Containers
| Container | Port | Status |
|-----------|------|--------|
| tflead-api | 127.0.0.1:8200->3000 | Up, healthy |
| tflead-mysql | 127.0.0.1:8206->3306 | Up, healthy |
| tflead-redis | 127.0.0.1:8279->6379 | Up, healthy |
| tflead-watchdog | — | Up, auto-heal verified |

### Module 1 — Signal Engine (completed 2026-04-05)
- Companies House daily scanner (10 SIC codes, MSP + Finance)
- Adzuna vacancy scanner (12 job titles, keys now active)
- Database job change tracker (weekly)
- Live test: 454 real UK prospects found and written to Google Sheet
- API: POST /signals/daily, POST /signals/weekly

### Module 2 — Personalisation Engine (completed 2026-04-05)
- Client research via Companies House + Tavily
- AI opener generator via Claude API (claude-sonnet-4-6)
- Live test: 3 openers generated (~£0.01), written to Sheet
- API: POST /personalise?limit=N

### Module 3 — Outreach Engine (completed 2026-04-05)
- MSP 5-email sequence (Day 0, 3, 7, 12, 18)
- Finance Broker 5-email sequence
- Outreach pusher with 50/day/client cap
- Follow-up engine for steps 2-5
- Live test: 3 DRY_RUN sends logged to Outreach_Log
- API: POST /outreach/push, POST /outreach/followups

### Module 4 — Client Delivery Layer (completed 2026-04-05)
- Calendly webhook handler (POST /webhooks/calendly)
- Weekly report (Claude-generated, Friday 5pm)
- Monthly ROI snapshot (28th of month)
- Telegram alerts on every booking
- API: POST /reports/weekly, POST /reports/monthly

### Module 5 — Talent Pool Upsell (completed 2026-04-06)
- Trigger: meetings >= 3, days on retainer >= 60
- 3 anonymised candidate matches per client
- Telegram alerts to client + Riz
- API: POST /upsell

### Module 6 — Website (completed 2026-04-05)
- Next.js 14 + Tailwind CSS, dark navy #0D1B2A + teal #00C896
- Pages: /, /msp, /finance-brokers, /how-it-works, /pricing, /book-audit
- Preview: http://204.168.162.1:8250
- Target: Vercel, domain tflead.co.uk pending

### Module 7 — Content Engine (completed 2026-04-06)
- Insight extractor (Monday 7am performance data)
- Content scheduler (Tuesday 8am, 2 LinkedIn drafts via Claude API)
- Drafts sent to Riz via Telegram for approval
- API: POST /content/insights, POST /content/schedule

### Pending Items
- Calendly API key (for webhook verification)
- Instantly account + domain (outreach@tflead.co.uk)
- tflead.co.uk domain purchase + Vercel DNS
- Cron jobs not yet configured (all triggers manual via API)
- DRY_RUN=true — Riz must set false to enable live sends

---

## PROJECT 3: TF Sales Talent (B2B Sales Candidate Platform)

**Repo:** github.com/RizTF/tf-sales-talent
**VPS directory:** /opt/tfsales/
**Port range:** 8100-8199 (8100=API, 8106=MySQL, 8179=Redis)
**Additional port:** 3333 (node server)
**Docker network:** tfsales-network
**Database:** tfsales_db (MySQL 8.0)
**Email:** hire@tfsales.co.uk

---

## PROJECT 4: Scout Bot (Outbound LinkedIn + Enrichment)

**Directory:** /home/scout/ — DO NOT MODIFY without Riz's permission
**Tech:** Node.js (scout.js + runner.js), Telegram-controlled
**LinkedIn:** HeyReach (Faruk primary InMail, James backup Sales Nav)
**Enrichment:** Prospeo, ContactOut
**LinkedIn API:** Unipile
**Cron:** unipile-inmail.js runs Mon-Fri at 10:00

---

## UK PRICING (all + VAT)

| Tier | Price | Salary Range |
|------|-------|-------------|
| Standard | £1,500 | Under £30k |
| Professional | £2,000 | £30k-£44,999 |
| Senior | £3,000 | £45k-£59,999 |
| Executive | £4,000 | £60k+ |

### Ireland Pricing (NO VAT)
| Tier | Price | Salary Range |
|------|-------|-------------|
| Standard | €1,800 | Under €30k |
| Professional | €2,300 | €30k-€44k |
| Senior | €3,300 | €45k-€59k |
| Executive | €4,300 | €60k+ |
| Replacement Add-On | €950 | — |

### 100% Refund Guarantee — IMPORTANT
- **THIS IS AN OPTIONAL ADD-ON** — NOT included as standard
- Additional insurance purchase the client opts into
- £750 + VAT when fee is £1,500; £1,000 + VAT for all other packages
- 12-month replacement guarantee
- **NEVER say the refund guarantee is included as standard**

### Key Selling Points vs Commission Agencies
- £40k role at 20% commission = £8,000. TalentFinder = £2,000. Saves £6,000
- £60k role at 20% commission = £12,000. TalentFinder = £4,000. Saves £8,000
- No risk, no lock-in, no percentage of salary

---

## PAUL'S EMAIL STYLE

- Warm, conversational, not corporate
- Short emails (under 150 words)
- Signs off as "Paul" only
- Never pushy — consultative approach
- References specific things about the recipient's company
- Ends with soft CTA (Calendly link or "happy to have a quick chat")
- Matches tone of sender

### Things to NEVER Say
- Never mention percentage-based fees or commission
- Never reference ISO 27001
- Never say the refund guarantee is included as standard
- Never promise specific candidates or timelines
- Never say "Paul from TalentFinder" or "The TalentFinder Team" — just "Paul"

---

## SERVICES & CREDENTIALS

| Service | Location | Notes |
|---------|----------|-------|
| Anthropic (Claude) | .env files | Model: claude-sonnet-4-6 |
| SMTP (Outlook) | /home/talentfinder/app/.env | paul@talentfinderuk.co.uk, smtp.office365.com:587 |
| Telegram | .env files | Chat ID: 1703019894 |
| ActiveCampaign | /home/talentfinder/app/.env | Suppress, unsub, tag contacts |
| Google Sheets (Pipeline) | /home/talentfinder/app/.env | Sheet: 1rxo_PLiTrJYNMMkgiO_NTxdEe33ev8mCpVasw_vZBZk |
| Google Sheets (Lead Engine) | /opt/tflead/.env | Sheet: 1QwM5Abw_cDkRZtyQmQWtbvqlQJDJ_c38tJSTtBsdWEc |
| Instantly | /opt/tflead/.env | Cold email platform, DRY_RUN=true |
| Companies House | /opt/tflead/.env | Signal Engine scanning |
| Adzuna | /opt/tflead/.env | Vacancy scanning |
| Prospeo | /home/scout/.env | Email enrichment |
| Unipile | /home/scout/.env | LinkedIn API |
| Webhook Server | systemd: tf-webhook | Port 5111 |
| Power Automate | External (M365) | 90-day trial, HTTP Premium |
| Microsoft Tenant | 148ba1ce-d2df-4456-9896-f97916cc687d | paul@talentfinderuk.co.uk |

---

## CRON JOBS

| Schedule | Command | Location |
|----------|---------|----------|
| Every 2 mins | inbox_watcher.py + telegram_handler.py | /etc/cron.d/talentfinder-engine |
| Every 2 hours | health_report.sh | /etc/cron.d/tf-health-report |
| Mon-Fri 10:00 | unipile-inmail.js | /home/scout/ crontab |

---

## PORTS IN USE

| Port | Service | Binding |
|------|---------|---------|
| 22 | SSH | 0.0.0.0 |
| 3333 | TF Sales node server | all interfaces |
| 5111 | TalentFinder webhook | 0.0.0.0 |
| 5678 | n8n | 0.0.0.0 |
| 8100 | tfsales-api | 127.0.0.1 |
| 8106 | tfsales-mysql | 127.0.0.1 |
| 8179 | tfsales-redis | 127.0.0.1 |
| 8200 | tflead-api | 127.0.0.1 |
| 8206 | tflead-mysql | 127.0.0.1 |
| 8250 | tflead website preview | — |
| 8279 | tflead-redis | 127.0.0.1 |

---

## BUILD PRINCIPLES

- Always run inside a named tmux session — never outside tmux
- Check tmux ls before starting — attach to existing session if it exists
- Send Telegram updates every 30 minutes during active builds
- Send Telegram BEFORE any action requiring Riz approval
- Test coverage minimum 80% on every module
- Never commit credentials — .env.example only
- Never push to main — always PR from feature branch
- DRY_RUN=true by default — Riz must explicitly set false
- Read this CLAUDE.md at the start of every session

---

## AUTONOMY RULES

- Make all technical decisions without asking
- Never ask about library choices, schema design, or error handling patterns
- Ask Riz ONLY for: credentials, confirmation before touching live systems
- If a test fails: fix it and re-run automatically
- If coverage drops below 80%: fix before moving to next module

---

## HOW TO MAINTAIN THIS FILE

1. Read first: At the start of every Claude Code session, read this file before doing anything
2. Update as you go: As you build, update this file when you discover something more current
3. Track what's live: After completing each module, append a summary
4. Sync with reality: If you read any config that reveals the real state, update this file
5. Never remove ring-fence rules
6. Never write actual credential values — structure and key names only
7. Flag conflicts: If anything conflicts with the filesystem, flag to Riz before proceeding
8. After significant changes, commit and push so all machines stay in sync
