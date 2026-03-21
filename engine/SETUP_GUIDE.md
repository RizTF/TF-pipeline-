# TalentFinder Sales Engine — Setup Guide

This guide walks you through setting up the inbound reply handler on your Hetzner VPS.
**No coding required** — you just fill in credentials and run one command.

---

## What This System Does

Watches Paul's Outlook inbox every 2 minutes. When a reply comes in:

| Reply Type | What Happens Automatically |
|---|---|
| **Positive** (wants info/booking) | Warm reply sent from Paul's inbox, ActiveCampaign sequence stopped, Riz notified on Telegram |
| **Question** (fees, process, etc.) | Claude answers automatically within minutes |
| **Complex** (needs judgement) | Claude drafts reply, Riz reviews on Telegram, replies SEND to approve |
| **Not Interested** | Suppressed in AC, polite close sent |
| **Unsubscribe** | Permanently removed from AC |
| **Wrong Person** | Tagged and suppressed |
| **Booking Confirmed** | Pre-call brief sent to Riz on Telegram |
| **Auto-reply / Bounce** | Silently ignored |

---

## Step 1: Get Your API Credentials

You need 4 things. Here's how to get each one:

### 1a. Anthropic API Key (Claude)
- Go to https://console.anthropic.com
- Sign in → API Keys → Create Key
- Copy the key (starts with `sk-ant-`)

### 1b. Telegram Bot Token
- Open Telegram, search for **@BotFather**
- Send `/newbot`
- Choose a name (e.g. "TF Sales Engine")
- Choose a username (e.g. "TFSalesEngineBot")
- BotFather gives you a token — copy it

### 1c. ActiveCampaign API Key
- Log into ActiveCampaign
- Go to Settings → Developer → API Access
- Copy both the **URL** and **Key**

### 1d. Google Sheets Service Account
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. In the sidebar: **APIs & Services → Library**
4. Search for and enable: **Google Sheets API** and **Google Drive API**
5. In the sidebar: **APIs & Services → Credentials**
6. Click **Create Credentials → Service Account**
7. Give it a name (e.g. "talentfinder-sheets")
8. Click **Done**
9. Click on the service account you just created
10. Go to **Keys** tab → **Add Key → Create new key → JSON**
11. A file downloads — rename it to `google_credentials.json`
12. **Important:** Copy the service account email (looks like `name@project.iam.gserviceaccount.com`)
13. Open your Google Sheet → Share → paste that email → give **Editor** access

---

## Step 2: Connect to Your VPS

Open a terminal (or use PuTTY on Windows) and run:

```
ssh root@YOUR_SERVER_IP
```

Enter your password when prompted.

---

## Step 3: Upload Files and Run Setup

From your local machine, upload the engine folder:

```
scp -r engine/ root@YOUR_SERVER_IP:/tmp/talentfinder-engine/
```

Then on the VPS:

```
cd /tmp/talentfinder-engine
bash scripts/setup.sh
```

This installs Python, creates the app directory, installs dependencies, and sets up cron jobs.

---

## Step 4: Fill In Your Credentials

On the VPS:

```
nano /home/talentfinder/app/.env
```

Fill in each value using the credentials from Step 1. Save with Ctrl+O, Enter, Ctrl+X.

---

## Step 5: Upload Google Credentials

From your local machine:

```
scp google_credentials.json root@YOUR_SERVER_IP:/home/talentfinder/app/config/
```

---

## Step 6: Get Telegram Chat ID

1. Open Telegram and send any message to your bot
2. On the VPS, run:

```
cd /home/talentfinder/app
venv/bin/python scripts/get_chat_ids.py
```

3. Copy the Chat ID shown
4. Edit `.env` and add it as `TELEGRAM_CHAT_ID`

---

## Step 7: Test Everything

```
cd /home/talentfinder/app
venv/bin/python scripts/test_connections.py
```

You should see:
- Claude API: **PASS**
- Telegram: **PASS**
- ActiveCampaign: **PASS**
- Google Sheets: **PASS**
- IMAP: **SKIP** (until Paul adds his password)
- SMTP: **SKIP** (until Paul adds his password)

---

## Step 8: Paul Adds His Email Password

Paul edits the `.env` file and adds his M365 password:

```
nano /home/talentfinder/app/.env
```

Find `EMAIL_PASSWORD=` and add his password.

**If MFA is enabled:** Paul must create an App Password at https://myaccount.microsoft.com → Security → App passwords. Use that 16-character password instead.

Run `test_connections.py` again — IMAP and SMTP should now show **PASS**.

---

## Step 9: Monitor

The system is now live. Check logs anytime:

```
tail -f /home/talentfinder/logs/inbox_watcher.log
```

---

## Telegram Commands for Riz

| Command | What It Does |
|---|---|
| `SEND draft_1` | Sends Claude's draft reply |
| `SKIP draft_1` | Discards the draft |

All other actions are fully automatic.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No emails detected | Check `EMAIL_PASSWORD` in `.env`. Run `test_connections.py`. |
| Telegram not working | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`. |
| Google Sheets error | Make sure you shared the sheet with the service account email. |
| Claude errors | Check `ANTHROPIC_API_KEY` and that you have credit on your Anthropic account. |
| Nothing in logs | Run `crontab -l` to verify cron jobs are installed. |
