#!/bin/bash
# ============================================================
# TalentFinder Sales Engine — VPS Setup Script
# ============================================================
# Run this on your Hetzner VPS as root:
#   bash scripts/setup.sh
# ============================================================

set -e

echo "============================================"
echo "  TalentFinder Sales Engine — Setup"
echo "============================================"
echo ""

# 1. System packages
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git -qq
echo "  Done."

# 2. Create app directory
echo "[2/5] Setting up application directory..."
APP_DIR="/home/talentfinder/app"
mkdir -p /home/talentfinder/{app,logs,data,config}

# If running from repo, copy engine files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$ENGINE_DIR/inbox_watcher.py" ]; then
    echo "  Copying engine files to $APP_DIR..."
    cp -r "$ENGINE_DIR"/* "$APP_DIR/"
    cp -r "$ENGINE_DIR"/.env.example "$APP_DIR/" 2>/dev/null || true
else
    echo "  WARNING: Run this script from the engine directory."
    echo "  Expected files in: $ENGINE_DIR"
    exit 1
fi
echo "  Done."

# 3. Python virtual environment
echo "[3/5] Creating Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Done."

# 4. Config file
echo "[4/5] Setting up configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "  Created .env file — YOU MUST EDIT THIS with your real credentials:"
    echo "    nano $APP_DIR/.env"
else
    echo "  .env file already exists — skipping."
fi
echo ""

# 5. Cron jobs
echo "[5/5] Setting up cron jobs..."
CRON_LINE_WATCHER="*/2 * * * * cd $APP_DIR && $APP_DIR/venv/bin/python inbox_watcher.py >> /home/talentfinder/logs/inbox_watcher.log 2>&1"
CRON_LINE_TELEGRAM="*/2 * * * * cd $APP_DIR && $APP_DIR/venv/bin/python telegram_handler.py >> /home/talentfinder/logs/telegram_handler.log 2>&1"

# Check if cron jobs already exist
if crontab -l 2>/dev/null | grep -q "inbox_watcher.py"; then
    echo "  Cron jobs already installed — skipping."
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE_WATCHER"; echo "$CRON_LINE_TELEGRAM") | crontab -
    echo "  Cron jobs installed."
fi

# Log rotation
cat > /etc/logrotate.d/talentfinder << 'LOGEOF'
/home/talentfinder/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGEOF
echo "  Log rotation configured."
echo ""

echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit your credentials:  nano $APP_DIR/.env"
echo "  2. Add Google credentials: upload google_credentials.json to $APP_DIR/config/"
echo "  3. Get Telegram chat ID:   cd $APP_DIR && venv/bin/python scripts/get_chat_ids.py"
echo "  4. Test connections:        cd $APP_DIR && venv/bin/python scripts/test_connections.py"
echo "  5. System is now running via cron every 2 minutes."
echo ""
echo "Monitor logs:  tail -f /home/talentfinder/logs/inbox_watcher.log"
echo ""
