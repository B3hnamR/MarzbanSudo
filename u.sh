#!/usr/bin/env bash
# update.sh — Safe updater for MarzbanSudo (bot + worker + logs)
#
# Usage:
#   ./update.sh                   # default: branch=main, target=all (bot then worker), tails bot logs
#   ./update.sh main bot          # update only bot (runs DB migrate first), tails bot logs
#   ./update.sh main worker       # update only worker (runs DB migrate first), tails worker logs#   ./update.sh main all worker   # update all, tail worker logs (3rd arg overrides which logs to follow)
#
# Requirements:
#   - Run from repository root (where docker-compose.yml exists)
#   - docker compose plugin available as `docker compose`

set -euo pipefail

BRANCH="${1:-main}"        # Git branch to deploy
TARGET="${2:-all}"         # bot|worker|all
TAIL_WHICH="${3:-auto}"    # auto|bot|worker

BOT_CTN="marzban_sudo_bot"
WRK_CTN="marzban_sudo_worker"
DB_SVC="db"

log() { printf "[*] %s\n" "$*"; }
err() { printf "[!] %s\n" "$*" >&2; }

# Wait for compose service container health (if healthcheck exists)
wait_for_healthy() {
  local svc="$1"
  local timeout="${2:-60}"
  local cname="marzban_sudo_${svc}"
  local start now status
  start="$(date +%s)"
  while true; do
    if ! docker inspect "$cname" >/dev/null 2>&1; then
      sleep 1
      continue
    fi
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cname" 2>/dev/null || echo "unknown")"
    if [[ "$status" == "healthy" || "$status" == "none" ]]; then
      break
    fi
    now="$(date +%s)"
    if (( now - start > timeout )); then
      err "$svc not healthy after ${timeout}s (status=$status), continuing anyway"
      break
    fi
    log "waiting for $svc to become healthy... (status=$status)"
    sleep 2
  done
}

recreate_service() {
  local svc="$1"
  log "Recreate $svc..."
  docker compose up -d --no-deps "$svc"
}

# --- Git update (auto-stash local changes) ---
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  log "Local changes detected; stashing..."
  git stash push -u -m "update.sh-pre-update-$(date -Iseconds)"
fi

log "Fetch/Pull $BRANCH..."
git fetch --all
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

# --- Ensure DB and build images ---
log "Ensure DB is up..."
docker compose up -d "$DB_SVC"
wait_for_healthy "$DB_SVC" 90

log "Build images (bot, worker)..."
docker compose build bot worker

# --- Migrations (safe to run always) ---
log "Run DB migrations..."
docker compose run --rm bot alembic upgrade head

# --- Deploy target ---
case "$TARGET" in
  bot)
    recreate_service bot
    ;;
  worker)
    recreate_service worker
    wait_for_healthy worker 30
    ;;
  all)
    # Start bot first (applies runtime init), then worker (scheduler)
    recreate_service bot
    recreate_service worker
    wait_for_healthy worker 30
    ;;
  *)
    err "Usage: $0 [branch=main] [bot|worker|all] [auto|bot|worker]"
    exit 1
    ;;
esac

# --- Tail logs ---
if [[ "$TAIL_WHICH" == "auto" ]]; then
  if [[ "$TARGET" == "worker" ]]; then
    TAIL_WHICH="worker"
  else
    TAIL_WHICH="bot"
  fi
fi

log "Tail logs ($TAIL_WHICH) — Ctrl+C to exit"
if [[ "$TAIL_WHICH" == "worker" ]]; then
  docker logs -f "$WRK_CTN"
else
  docker logs -f "$BOT_CTN"
fi