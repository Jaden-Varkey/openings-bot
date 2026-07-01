#!/usr/bin/env bash
# Cron wrapper for the always-on VM deployment.
#
# - cd's into the project so `python -m watcher.main` resolves and state lands in
#   ./state/seen.json
# - loads notification secrets from .env
# - uses flock so a slow run can never overlap the next 2-min tick (no double
#   alerts, no corrupted state)
#
# Wire it up in crontab (see deploy/crontab.example):
#   */2 * * * * /full/path/to/openings-bot/run.sh >> /full/path/to/openings-bot/cron.log 2>&1
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

# Single-instance lock; bail quietly if the previous tick is still running.
exec 9>/tmp/openings-bot.lock
if ! flock -n 9; then
    echo "$(date -u +%FT%TZ) skip: previous run still in progress"
    exit 0
fi

# Load secrets (EMAIL_*, TELEGRAM_*) without echoing them.
set -a
[ -f .env ] && . ./.env
set +a

# Prefer the project venv if present, else system python3.
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

echo "$(date -u +%FT%TZ) run start"
"$PY" -m watcher.main --once
echo "$(date -u +%FT%TZ) run done"
