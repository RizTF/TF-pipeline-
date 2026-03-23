#!/bin/bash
# ============================================================
# TalentFinder Sales Engine — Remote Deploy Script
# ============================================================
# Run from your LOCAL machine (laptop/desktop) to deploy the
# engine to your Hetzner VPS in a single command.
#
# Usage:
#   bash engine/scripts/deploy.sh <VPS_IP> [SSH_USER]
#
# Examples:
#   bash engine/scripts/deploy.sh 65.21.xxx.xxx
#   bash engine/scripts/deploy.sh 65.21.xxx.xxx root
# ============================================================

set -e

VPS_IP="${1:?Usage: deploy.sh <VPS_IP> [SSH_USER]}"
SSH_USER="${2:-root}"
REMOTE="$SSH_USER@$VPS_IP"
APP_DIR="/home/talentfinder/app"

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  TalentFinder Engine — Remote Deploy"
echo "============================================"
echo ""
echo "  Target: $REMOTE"
echo "  Engine: $ENGINE_DIR"
echo ""

# Sanity check
if [ ! -f "$ENGINE_DIR/inbox_watcher.py" ]; then
    echo "ERROR: Cannot find engine files at $ENGINE_DIR"
    echo "Run this script from the repo root: bash engine/scripts/deploy.sh <IP>"
    exit 1
fi

# 1. Upload engine files
echo "[1/4] Uploading engine files to VPS..."
ssh "$REMOTE" "mkdir -p $APP_DIR/{config,data,logs,scripts,modules}"
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.env' \
    "$ENGINE_DIR/" "$REMOTE:$APP_DIR/"
echo "  Done."

# 2. Run setup on remote
echo "[2/4] Running setup on VPS..."
ssh "$REMOTE" "cd $APP_DIR && bash scripts/setup.sh"
echo "  Done."

# 3. Check if .env needs credentials
echo "[3/4] Checking .env configuration..."
NEEDS_EDIT=$(ssh "$REMOTE" "grep -c 'your-.*-here\|CHANGEME\|^[A-Z_]*=$' $APP_DIR/.env 2>/dev/null || echo 0")
if [ "$NEEDS_EDIT" -gt 0 ]; then
    echo ""
    echo "  WARNING: Your .env file has $NEEDS_EDIT unconfigured values."
    echo "  SSH in and edit:  ssh $REMOTE 'nano $APP_DIR/.env'"
    echo ""
fi

# 4. Test connections
echo "[4/4] Testing API connections..."
ssh "$REMOTE" "cd $APP_DIR && venv/bin/python scripts/test_connections.py" || true

echo ""
echo "============================================"
echo "  Deploy complete!"
echo "============================================"
echo ""
echo "Useful commands:"
echo "  ssh $REMOTE 'tail -f /home/talentfinder/logs/inbox_watcher.log'"
echo "  ssh $REMOTE 'crontab -l'"
echo "  ssh $REMOTE 'nano $APP_DIR/.env'"
echo ""
