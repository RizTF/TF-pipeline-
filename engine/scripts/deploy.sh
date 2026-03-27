#!/bin/bash
# ============================================================
# TalentFinder Sales Engine — Remote Deploy Script
# ============================================================
# Run from your LOCAL machine (Git Bash / laptop) to deploy the
# inbound reply engine to your VPS alongside Scout.
#
# Usage:
#   bash engine/scripts/deploy.sh
#   bash engine/scripts/deploy.sh <VPS_IP> [SSH_USER]
#
# Defaults: 204.168.162.1 / root
# ============================================================

set -e

VPS_IP="${1:-204.168.162.1}"
SSH_USER="${2:-root}"
REMOTE="$SSH_USER@$VPS_IP"
APP_DIR="/home/talentfinder/app"
SCOUT_CREDS="/home/scout/google_credentials.json"

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  TalentFinder Inbound Engine — Deploy"
echo "============================================"
echo ""
echo "  Target:  $REMOTE"
echo "  Engine:  $ENGINE_DIR"
echo "  Install: $APP_DIR"
echo ""

# Sanity check
if [ ! -f "$ENGINE_DIR/inbox_watcher.py" ]; then
    echo "ERROR: Cannot find engine files at $ENGINE_DIR"
    echo "Run this script from the repo root: bash engine/scripts/deploy.sh"
    exit 1
fi

# 1. Upload engine files (including .env)
echo "[1/5] Uploading engine files to VPS..."
ssh "$REMOTE" "mkdir -p $APP_DIR/{config,data,logs,scripts,modules}"
rsync -avz --exclude='venv' --exclude='__pycache__' \
    "$ENGINE_DIR/" "$REMOTE:$APP_DIR/"
echo "  Done."

# 2. Link Google credentials from Scout
echo "[2/5] Linking Google credentials from Scout..."
ssh "$REMOTE" "
    if [ -f $SCOUT_CREDS ]; then
        cp $SCOUT_CREDS $APP_DIR/config/google_credentials.json
        echo '  Copied from $SCOUT_CREDS'
    else
        echo '  WARNING: $SCOUT_CREDS not found — Sheets logging will be disabled'
    fi
"
echo "  Done."

# 3. Python environment
echo "[3/5] Setting up Python environment..."
ssh "$REMOTE" "
    cd $APP_DIR
    apt-get install -y python3 python3-pip python3-venv -qq 2>/dev/null
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
    venv/bin/pip install --upgrade pip -q
    venv/bin/pip install -r requirements.txt -q
"
echo "  Done."

# 4. Cron jobs (inbox_watcher + telegram_handler every 2 min)
echo "[4/5] Setting up cron jobs..."
ssh "$REMOTE" "
    CRON_FILE='/etc/cron.d/talentfinder-engine'
    cat > \$CRON_FILE << 'CRONEOF'
# TalentFinder Inbound Reply Engine — runs every 2 minutes
*/2 * * * * root cd /home/talentfinder/app && /home/talentfinder/app/venv/bin/python inbox_watcher.py >> /home/talentfinder/logs/inbox_watcher.log 2>&1
*/2 * * * * root cd /home/talentfinder/app && /home/talentfinder/app/venv/bin/python telegram_handler.py >> /home/talentfinder/logs/telegram_handler.log 2>&1
CRONEOF
    chmod 644 \$CRON_FILE
    echo '  Cron jobs written to /etc/cron.d/talentfinder-engine'
"

# Log rotation
ssh "$REMOTE" "
    cat > /etc/logrotate.d/talentfinder << 'LOGEOF'
/home/talentfinder/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGEOF
"
echo "  Done."

# 5. Test connections
echo "[5/5] Testing API connections..."
ssh "$REMOTE" "cd $APP_DIR && venv/bin/python scripts/test_connections.py" || true

echo ""
echo "============================================"
echo "  Deploy complete!"
echo "============================================"
echo ""
echo "Monitor:"
echo "  ssh $REMOTE 'tail -f /home/talentfinder/logs/inbox_watcher.log'"
echo "  ssh $REMOTE 'tail -f /home/talentfinder/logs/telegram_handler.log'"
echo ""
echo "Manage:"
echo "  ssh $REMOTE 'cat /etc/cron.d/talentfinder-engine'"
echo "  ssh $REMOTE 'nano $APP_DIR/.env'"
echo "  ssh $REMOTE 'cd $APP_DIR && venv/bin/python scripts/test_connections.py'"
echo ""
