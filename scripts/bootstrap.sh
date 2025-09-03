#!/usr/bin/env bash
set -euo pipefail

# MarzbanSudo bootstrapper for a fresh Linux server
# - Installs Docker & Docker Compose (v2)
# - Prepares .env (copies from .env.example if missing)
# - Applies env overrides from current shell to .env (if provided)
# - Creates required directories
# - Brings up services with docker compose
# - Waits for healthchecks and tails logs
#
# Usage:
#   bash scripts/bootstrap.sh
#   TELEGRAM_BOT_TOKEN=XXXX MARZBAN_BASE_URL=https://... bash scripts/bootstrap.sh
#
# Notes:
# - Run as root (or with sudo)
# - If you want non-interactive run, export required vars beforehand

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

need_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "[!] Please run as root (sudo)" >&2
    exit 1
  fi
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

install_docker() {
  if have_cmd docker; then
    echo "[*] Docker already installed: $(docker --version)"
    return
  fi
  echo "[*] Installing Docker using official convenience script ..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  rm -f get-docker.sh
  systemctl enable docker || true
  systemctl start docker || true
  echo "[*] Docker installed: $(docker --version)"
}

ensure_compose() {
  # Prefer 'docker compose' (v2). If not available, attempt to install plugin.
  if docker compose version >/dev/null 2>&1; then
    echo "[*] Docker Compose v2 available: $(docker compose version | head -n1)"
    return
  fi
  echo "[*] Docker Compose v2 not found; attempting to install plugin (if supported) ..."
  # On many systems, compose v2 is included with Docker engine >= 20.10
  # Re-check after service restart
  systemctl restart docker || true
  sleep 2
  if docker compose version >/dev/null 2>&1; then
    echo "[*] Docker Compose v2 available after restart"
    return
  fi
  echo "[!] 'docker compose' not found. Please ensure Docker engine with Compose v2 is installed."
  exit 1
}

ensure_env_file() {
  if [ ! -f .env ]; then
    echo "[*] .env not found; copying from .env.example"
    cp -n .env.example .env
  fi
}

set_env_var() {
  # set_env_var KEY VALUE -> updates .env in place (adds if missing)
  local key="$1"; shift
  local val="$*"
  local esc_val
  # Escape for sed (slashes)
  esc_val=$(printf '%s' "$val" | sed -e 's/[\\&]/\\&/g')
  if grep -qE "^${key}=" .env; then
    sed -i -E "s|^${key}=.*$|${key}=${esc_val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

apply_env_overrides() {
  echo "[*] Applying environment overrides to .env (if provided)"
  # List of commonly provided variables; extend as needed
  for key in \
    TELEGRAM_BOT_TOKEN TELEGRAM_ADMIN_IDS \
    MARZBAN_BASE_URL MARZBAN_ADMIN_USERNAME MARZBAN_ADMIN_PASSWORD \
    DB_URL DB_PASSWORD DB_ROOT_PASSWORD \
    SUB_DOMAIN_PREFERRED LOG_CHAT_ID APP_ENV TZ \
    NOTIFY_USAGE_THRESHOLDS NOTIFY_EXPIRY_DAYS RATE_LIMIT_USER_MSG_PER_MIN \
    CLEANUP_EXPPIRED_AFTER_DAYS PENDING_ORDER_AUTOCANCEL_HOURS RECEIPT_RETENTION_DAYS \
    TRIAL_ENABLED TRIAL_TEMPLATE_ID TRIAL_DATA_GB TRIAL_DURATION_DAYS \
    ADMIN_CAPS_DEFAULT
  do
    if [ -n "${!key-}" ]; then
      set_env_var "$key" "${!key}"
    fi
  done
}

prepare_dirs() {
  mkdir -p logs data
  chmod 755 logs data || true
}

compose_down() {
  echo "[*] Bringing down any existing stack ..."
  docker compose down -v || true
}

compose_up() {
  echo "[*] Building and starting services ..."
  docker compose up -d --build
}

wait_for_health() {
  local name="$1"; shift
  local timeout="${1:-180}"
  local elapsed=0
  echo "[*] Waiting for container '$name' to become healthy (timeout ${timeout}s) ..."
  while true; do
    local st
    st=$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || true)
    if [ "$st" = "healthy" ]; then
      echo "[*] $name is healthy"
      break
    fi
    if [ "$st" = "unhealthy" ]; then
      echo "[!] $name is unhealthy" >&2
      docker logs --tail 100 "$name" || true
      exit 1
    fi
    sleep 3
    elapsed=$((elapsed+3))
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "[!] Timeout waiting for $name to be healthy (last status: $st)" >&2
      docker logs --tail 100 "$name" || true
      exit 1
    fi
  done
}

follow_logs() {
  echo "[*] Tailing bot logs (Ctrl-C to exit) ..."
  docker logs -f --tail 100 marzban_sudo_bot || true
}

main() {
  need_root
  install_docker
  ensure_compose
  ensure_env_file
  apply_env_overrides
  prepare_dirs
  compose_down
  compose_up
  # Wait for DB, then bot and worker
  wait_for_health marzban_sudo_db 180
  wait_for_health marzban_sudo_bot 180
  wait_for_health marzban_sudo_worker 180 || true
  echo "[*] Stack is up. Healthchecks passed."
  echo "[*] You can now message your bot on Telegram."
  echo "[*] To reconfigure, edit .env and run: docker compose up -d --build"
  follow_logs
}

main "$@"
