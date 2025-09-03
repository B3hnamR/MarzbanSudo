#!/usr/bin/env bash
set -euo pipefail

# Interactive setup for MarzbanSudo
# - Prompts for required values and writes .env
# - Creates .env from .env.example if missing
# - Optionally runs bootstrap.sh to deploy
#
# Usage:
#   bash scripts/setup.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_env_file() {
  if [ ! -f .env ]; then
    echo "[*] .env not found; copying from .env.example"
    cp -n .env.example .env
  fi
}

get_env() {
  # get_env KEY -> prints current value from .env if exists
  local key="$1"
  if [ -f .env ]; then
    # shellcheck disable=SC2002
    cat .env | grep -E "^${key}=" | head -n1 | sed -E "s/^${key}=//" || true
  fi
}

set_env_var() {
  # set_env_var KEY VALUE -> updates .env in place (adds if missing)
  local key="$1"; shift
  local val="$*"
  local esc_val
  esc_val=$(printf '%s' "$val" | sed -e 's/[\\&]/\\&/g')
  if grep -qE "^${key}=" .env; then
    sed -i -E "s|^${key}=.*$|${key}=${esc_val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

prompt() {
  # prompt "Question" default -> echoes value
  local q="$1"; shift
  local def="${1-}"
  local ans
  if [ -n "$def" ]; then
    read -r -p "$q [$def]: " ans || true
    echo "${ans:-$def}"
  else
    read -r -p "$q: " ans || true
    echo "$ans"
  fi
}

prompt_secret() {
  local q="$1"; shift
  local def="${1-}"
  local ans
  if [ -n "$def" ]; then
    read -r -s -p "$q [hidden, press Enter to keep current]: " ans || true; echo
    if [ -z "$ans" ]; then echo "$def"; else echo "$ans"; fi
  else
    read -r -s -p "$q [hidden]: " ans || true; echo
    echo "$ans"
  fi
}

require_nonempty() {
  local name="$1"; shift
  local val="$*"
  if [ -z "$val" ]; then
    echo "[!] $name is required. Aborting." >&2
    exit 1
  fi
}

header() {
  echo
  echo "========================================"
  echo "$*"
  echo "========================================"
}

main() {
  header "MarzbanSudo interactive setup"
  ensure_env_file

  # Defaults from current .env if present
  local def_APP_ENV def_TZ def_TBT def_TADM def_LOG_CHAT_ID def_REQ_CH def_PV
  local def_MZ_URL def_MZ_USER def_MZ_PASS
  local def_DB_URL def_DB_PASS def_DB_ROOT
  local def_SUB_DOMAIN def_NOTIF_T def_NOTIF_E def_RATE def_CLEAN def_AUTO def_RET def_TRIAL def_TRIAL_TID def_TRIAL_GB def_TRIAL_DAYS def_CAPS

  def_APP_ENV="$(get_env APP_ENV || echo production)"
  def_TZ="$(get_env TZ || echo Asia/Tehran)"
  def_TBT="$(get_env TELEGRAM_BOT_TOKEN || true)"
  def_TADM="$(get_env TELEGRAM_ADMIN_IDS || true)"
  def_LOG_CHAT_ID="$(get_env LOG_CHAT_ID || true)"
  def_REQ_CH="$(get_env REQUIRED_CHANNEL || true)"
  def_PV="$(get_env PHONE_VERIFICATION_ENABLED || echo 0)"

  def_MZ_URL="$(get_env MARZBAN_BASE_URL || true)"
  def_MZ_USER="$(get_env MARZBAN_ADMIN_USERNAME || true)"
  def_MZ_PASS="$(get_env MARZBAN_ADMIN_PASSWORD || true)"

  def_DB_URL="$(get_env DB_URL || true)"
  def_DB_PASS="$(get_env DB_PASSWORD || true)"
  def_DB_ROOT="$(get_env DB_ROOT_PASSWORD || true)"

  def_SUB_DOMAIN="$(get_env SUB_DOMAIN_PREFERRED || true)"
  def_NOTIF_T="$(get_env NOTIFY_USAGE_THRESHOLDS || echo 0.7,0.9)"
  def_NOTIF_E="$(get_env NOTIFY_EXPIRY_DAYS || echo 3,1,0)"
  def_RATE="$(get_env RATE_LIMIT_USER_MSG_PER_MIN || echo 20)"
  def_CLEAN="$(get_env CLEANUP_EXPIRED_AFTER_DAYS || echo 7)"
  def_AUTO="$(get_env PENDING_ORDER_AUTOCANCEL_HOURS || echo 12)"
  def_RET="$(get_env RECEIPT_RETENTION_DAYS || echo 30)"
  def_TRIAL="$(get_env TRIAL_ENABLED || echo 1)"
  def_TRIAL_TID="$(get_env TRIAL_TEMPLATE_ID || echo 1)"
  def_TRIAL_GB="$(get_env TRIAL_DATA_GB || echo 2)"
  def_TRIAL_DAYS="$(get_env TRIAL_DURATION_DAYS || echo 1)"
  def_CAPS="$(get_env ADMIN_CAPS_DEFAULT || echo *)"

  echo "[*] Press Enter to keep defaults from current .env (if any)." 

  # General
  APP_ENV="$(prompt "Application environment (production/staging/development)" "$def_APP_ENV")"
  TZ="$(prompt "Timezone" "$def_TZ")"

  # Telegram
  TELEGRAM_BOT_TOKEN="$(prompt_secret "TELEGRAM_BOT_TOKEN" "$def_TBT")"
  TELEGRAM_ADMIN_IDS="$(prompt "TELEGRAM_ADMIN_IDS (comma-separated numeric IDs)" "$def_TADM")"
  LOG_CHAT_ID="$(prompt "LOG_CHAT_ID (optional)" "$def_LOG_CHAT_ID")"
  REQUIRED_CHANNEL="$(prompt "REQUIRED_CHANNEL (optional @channel_username)" "$def_REQ_CH")"
  PHONE_VERIFICATION_ENABLED="$(prompt "PHONE_VERIFICATION_ENABLED (0/1)" "$def_PV")"

  # Marzban
  MARZBAN_BASE_URL="$(prompt "MARZBAN_BASE_URL (e.g., https://panel.domain)" "$def_MZ_URL")"
  MARZBAN_ADMIN_USERNAME="$(prompt "MARZBAN_ADMIN_USERNAME" "$def_MZ_USER")"
  MARZBAN_ADMIN_PASSWORD="$(prompt_secret "MARZBAN_ADMIN_PASSWORD" "$def_MZ_PASS")"

  # Database
  DB_PASSWORD="$(prompt_secret "DB_PASSWORD (for MariaDB user 'sudo_user')" "$def_DB_PASS")"
  DB_ROOT_PASSWORD="$(prompt_secret "DB_ROOT_PASSWORD (for MariaDB root)" "$def_DB_ROOT")"
  local suggested_DB_URL="mysql+asyncmy://sudo_user:${DB_PASSWORD}@db:3306/marzban_sudo?charset=utf8mb4"
  DB_URL="$(prompt "DB_URL" "${def_DB_URL:-$suggested_DB_URL}")"

  # Optional business settings
  SUB_DOMAIN_PREFERRED="$(prompt "SUB_DOMAIN_PREFERRED (for subscription links)" "$def_SUB_DOMAIN")"
  NOTIFY_USAGE_THRESHOLDS="$(prompt "NOTIFY_USAGE_THRESHOLDS (e.g., 0.7,0.9)" "$def_NOTIF_T")"
  NOTIFY_EXPIRY_DAYS="$(prompt "NOTIFY_EXPIRY_DAYS (e.g., 3,1,0)" "$def_NOTIF_E")"
  RATE_LIMIT_USER_MSG_PER_MIN="$(prompt "RATE_LIMIT_USER_MSG_PER_MIN" "$def_RATE")"
  CLEANUP_EXPIRED_AFTER_DAYS="$(prompt "CLEANUP_EXPIRED_AFTER_DAYS" "$def_CLEAN")"
  PENDING_ORDER_AUTOCANCEL_HOURS="$(prompt "PENDING_ORDER_AUTOCANCEL_HOURS" "$def_AUTO")"
  RECEIPT_RETENTION_DAYS="$(prompt "RECEIPT_RETENTION_DAYS" "$def_RET")"
  TRIAL_ENABLED="$(prompt "TRIAL_ENABLED (0/1)" "$def_TRIAL")"
  TRIAL_TEMPLATE_ID="$(prompt "TRIAL_TEMPLATE_ID" "$def_TRIAL_TID")"
  TRIAL_DATA_GB="$(prompt "TRIAL_DATA_GB" "$def_TRIAL_GB")"
  TRIAL_DURATION_DAYS="$(prompt "TRIAL_DURATION_DAYS" "$def_TRIAL_DAYS")"
  ADMIN_CAPS_DEFAULT="$(prompt "ADMIN_CAPS_DEFAULT (* or CSV of caps)" "$def_CAPS")"

  # Required validations
  require_nonempty TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
  require_nonempty TELEGRAM_ADMIN_IDS "$TELEGRAM_ADMIN_IDS"
  require_nonempty MARZBAN_BASE_URL "$MARZBAN_BASE_URL"
  require_nonempty MARZBAN_ADMIN_USERNAME "$MARZBAN_ADMIN_USERNAME"
  require_nonempty MARZBAN_ADMIN_PASSWORD "$MARZBAN_ADMIN_PASSWORD"
  require_nonempty DB_PASSWORD "$DB_PASSWORD"
  require_nonempty DB_ROOT_PASSWORD "$DB_ROOT_PASSWORD"
  require_nonempty DB_URL "$DB_URL"

  header "Writing .env"
  set_env_var APP_ENV "$APP_ENV"
  set_env_var TZ "$TZ"
  set_env_var TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
  set_env_var TELEGRAM_ADMIN_IDS "$TELEGRAM_ADMIN_IDS"
  set_env_var LOG_CHAT_ID "$LOG_CHAT_ID"
  set_env_var REQUIRED_CHANNEL "$REQUIRED_CHANNEL"
  set_env_var PHONE_VERIFICATION_ENABLED "$PHONE_VERIFICATION_ENABLED"

  set_env_var MARZBAN_BASE_URL "$MARZBAN_BASE_URL"
  set_env_var MARZBAN_ADMIN_USERNAME "$MARZBAN_ADMIN_USERNAME"
  set_env_var MARZBAN_ADMIN_PASSWORD "$MARZBAN_ADMIN_PASSWORD"

  set_env_var DB_URL "$DB_URL"
  set_env_var DB_PASSWORD "$DB_PASSWORD"
  set_env_var DB_ROOT_PASSWORD "$DB_ROOT_PASSWORD"

  set_env_var SUB_DOMAIN_PREFERRED "$SUB_DOMAIN_PREFERRED"
  set_env_var NOTIFY_USAGE_THRESHOLDS "$NOTIFY_USAGE_THRESHOLDS"
  set_env_var NOTIFY_EXPIRY_DAYS "$NOTIFY_EXPIRY_DAYS"
  set_env_var RATE_LIMIT_USER_MSG_PER_MIN "$RATE_LIMIT_USER_MSG_PER_MIN"
  set_env_var CLEANUP_EXPIRED_AFTER_DAYS "$CLEANUP_EXPIRED_AFTER_DAYS"
  set_env_var PENDING_ORDER_AUTOCANCEL_HOURS "$PENDING_ORDER_AUTOCANCEL_HOURS"
  set_env_var RECEIPT_RETENTION_DAYS "$RECEIPT_RETENTION_DAYS"
  set_env_var TRIAL_ENABLED "$TRIAL_ENABLED"
  set_env_var TRIAL_TEMPLATE_ID "$TRIAL_TEMPLATE_ID"
  set_env_var TRIAL_DATA_GB "$TRIAL_DATA_GB"
  set_env_var TRIAL_DURATION_DAYS "$TRIAL_DURATION_DAYS"
  set_env_var ADMIN_CAPS_DEFAULT "$ADMIN_CAPS_DEFAULT"

  echo "[*] .env updated successfully."

  echo
  read -r -p "Run deployment now (install docker/compose if needed and start stack)? [Y/n]: " ANSW || true
  ANSW=${ANSW:-Y}
  if [[ "$ANSW" =~ ^[Yy]$ ]]; then
    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
      echo "[!] Deployment requires root privileges. Re-run with sudo:"
      echo "    sudo bash scripts/bootstrap.sh"
      exit 0
    fi
    bash scripts/bootstrap.sh
  else
    echo "[*] You can deploy later by running: bash scripts/bootstrap.sh"
  fi
}

main "$@"
