#!/bin/bash
# ============================================================
# TalentFinder Sales Engine — VPS Setup Script
# ============================================================
# Run this DIRECTLY on the VPS if not using deploy.sh:
#   cd /home/talentfinder/app && bash scripts/setup.sh
# ============================================================

set -e

APP_DIR="/home/talentfinder/app"
SCOUT_CREDS="/home/scout/google_credentials.json"

echo "============================================"
echo "  TalentFinder Inbound Engine — Setup"
echo "============================================"
echo ""

# 1. System packages
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git -qq
echo "  Done."

# 2. Create directories
echo "[2/6] Setting up directories..."
mkdir -p /home/talentfinder/{app,logs,data}
mkdir -p $APP_DIR/{config,data,logs,scripts,modules}
echo "  Done."

# 3. Google credentials
echo "[3/6] Setting up Google credentials..."
if [ -f "$APP_DIR/config/google_credentials.json" ]; then
    echo "  Already present."
elif [ -f "$SCOUT_CREDS" ]; then
    cp "$SCOUT_CREDS" "$APP_DIR/config/google_credentials.json"
    echo "  Copied from Scout: $SCOUT_CREDS"
else
    echo "  WARNING: No Google credentials found."
    echo "  Sheets logging will be disabled until you add:"
    echo "    $APP_DIR/config/google_credentials.json"
fi

# 4. Python virtual environment
echo "[4/6] Creating Python virtual environment..."
cd "$APP_DIR"
if [ ! -d venv ]; then
    python3 -m venv venv
fi
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "  Done."

# 5. Config file
echo "[5/6] Checking configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.example" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        echo "  Created .env from template — EDIT with real credentials:"
        echo "    nano $APP_DIR/.env"
    else
        echo "  WARNING: No .env file found. Upload one before running."
    fi
else
    echo "  .env file present."
fi

# 6. Cron jobs
echo "[6/6] Setting up cron jobs..."
CRON_FILE="/etc/cron.d/talentfinder-engine"
cat > "$CRON_FILE" << 'CRONEOF'
# TalentFinder Inbound Reply Engine — runs every 2 minutes
*/2 * * * * root cd /home/talentfinder/app && /home/talentfinder/app/venv/bin/python inbox_watcher.py >> /home/talentfinder/logs/inbox_watcher.log 2>&1
*/2 * * * * root cd /home/talentfinder/app && /home/talentfinder/app/venv/bin/python telegram_handler.py >> /home/talentfinder/logs/telegram_handler.log 2>&1
CRONEOF
chmod 644 "$CRON_FILE"
echo "  Cron jobs written to $CRON_FILE"

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
echo "  1. Check .env:       nano $APP_DIR/.env"
echo "  2. Test connections:  cd $APP_DIR && venv/bin/python scripts/test_connections.py"
echo "  3. Engine runs automatically via cron every 2 minutes."
echo ""
echo "Monitor:"
echo "  tail -f /home/talentfinder/logs/inbox_watcher.log"
echo "  tail -f /home/talentfinder/logs/telegram_handler.log"
echo ""
