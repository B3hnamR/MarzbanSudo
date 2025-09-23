#!/usr/bin/env bash
set -euo pipefail

# Interactive setup for MarzbanSudo
# - Prompts for required values and writes .env
# - Creates .env from .env.example if missing
# - Optional UI via whiptail/dialog (falls back to plain prompts)
# - Supports modes: simple | advanced
# - Non-interactive via flags/ENV for CI
#
# Usage:
#   bash scripts/setup.sh [--mode simple|advanced] [--non-interactive|-y]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_env_file() {
  if [ ! -f .env ]; then
    echo "[*] .env not found; copying from .env.example"
    if [ -f .env.example ]; then cp .env.example .env; else touch .env; fi
  fi
}

get_env() {
  # get_env KEY -> prints current value from .env if exists; fallback to current process env
  local key="$1"
  if [ -f .env ]; then
    # shellcheck disable=SC2002
    cat .env | grep -E "^${key}=" | head -n1 | sed -E "s/^${key}=//" || true
  fi
  if [ -n "${!key-}" ]; then
    printf '%s\n' "${!key}"
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

set_env_if_missing() {
  # set_env_if_missing KEY VALUE -> only writes if KEY is absent
  local key="$1"; shift
  local val="$*"
  if ! grep -qE "^${key}=" .env; then
    echo "${key}=${val}" >> .env
  fi
}

# Password and URL helpers
gen_password() {
  local len="${1:-24}"
  LC_ALL=C tr -dc '-A-Za-z0-9@#%+=_.' < /dev/urandom | head -c "$len" || true
  echo
}

urlencode() {
  local s="$1"
  local out=""
  local i c
  for (( i=0; i<${#s}; i++ )); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) out+="$c" ;;
      *) printf -v hex '%%%02X' "'$c"; out+="$hex" ;;
    esac
  done
  printf '%s' "$out"
}

# Validation helpers
validate_admin_ids() { [[ "$1" =~ ^[0-9]+(,[0-9]+)*$ ]]; }
validate_url() { [[ "$1" =~ ^https?://[^\ ]+$ ]]; }
validate_channel() { [[ -z "$1" || "$1" =~ ^@[^\ ]+$ ]]; }
validate_db_url() { [[ "$1" =~ ^mysql\+asyncmy://.+@.+/.+\?charset=utf8mb4(\&.*)?$ ]]; }

require_nonempty() {
  local name="$1"; shift
  local val="$*"
  if [ -z "$val" ]; then
    echo "[!] $name is required. Aborting." >&2
    exit 1
  fi
}

# UI and CLI parsing
UI="${SETUP_UI:-none}"
NON_INTERACTIVE="0"
MODE=""

ui_detect() {
  UI="${SETUP_UI:-none}"
  if [ "$UI" = "auto" ]; then
    if have_cmd whiptail; then UI="whiptail"; elif have_cmd dialog; then UI="dialog"; else UI="none"; fi
  fi
}

ui_yesno() {
  local q="$1"
  if [ "$UI" = "whiptail" ]; then
    whiptail --title "MarzbanSudo Setup" --yesno "$q" 10 72
    return $?
  elif [ "$UI" = "dialog" ]; then
    dialog --title "MarzbanSudo Setup" --yesno "$q" 10 72
    return $?
  else
    read -r -p "$q [Y/n]: " _a || true
    _a=${_a:-Y}
    [[ "$_a" =~ ^[Yy]$ ]]
    return $?
  fi
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --mode)
        MODE="${2:-}"; shift 2 ;;
      --mode=*)
        MODE="${1#*=}"; shift ;;
      --non-interactive|--yes|-y)
        NON_INTERACTIVE="1"; shift ;;
      *) shift ;;
    esac
  done
}

prompt() {
  # prompt "Question" default -> echoes value
  local q="$1"; shift
  local def="${1-}"
  local ans
  if [ "$NON_INTERACTIVE" = "1" ]; then
    printf '%s\n' "${def}"
    return 0
  fi
  if [ "$UI" = "whiptail" ]; then
    ans=$(whiptail --title "MarzbanSudo Setup" --inputbox "$q" 10 72 "$def" 3>&1 1>&2 2>&3) || ans="$def"
    printf '%s\n' "${ans:-$def}"
    return 0
  elif [ "$UI" = "dialog" ]; then
    ans=$(dialog --title "MarzbanSudo Setup" --inputbox "$q" 10 72 "$def" 3>&1 1>&2 2>&3) || ans="$def"
    printf '%s\n' "${ans:-$def}"
    return 0
  fi
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
  if [ "$NON_INTERACTIVE" = "1" ]; then
    printf '%s\n' "${def}"
    return 0
  fi
  if [ "$UI" = "whiptail" ]; then
    ans=$(whiptail --title "MarzbanSudo Setup" --passwordbox "$q" 10 72 3>&1 1>&2 2>&3) || ans="$def"
    printf '%s\n' "${ans:-$def}"
    return 0
  elif [ "$UI" = "dialog" ]; then
    ans=$(dialog --title "MarzbanSudo Setup" --passwordbox "$q" 10 72 3>&1 1>&2 2>&3) || ans="$def"
    printf '%s\n' "${ans:-$def}"
    return 0
  fi
  if [ -n "$def" ]; then
    read -r -s -p "$q [hidden, press Enter to keep current]: " ans || true; echo
    if [ -z "$ans" ]; then echo "$def"; else echo "$ans"; fi
  else
    read -r -s -p "$q [hidden]: " ans || true; echo
    echo "$ans"
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

  parse_args "$@"
  ui_detect
  if [ -z "${MODE:-}" ]; then
    if [ "$NON_INTERACTIVE" = "1" ]; then
      MODE="simple"
    else
      MODE="$(prompt "Mode (simple/advanced)" "simple")"
    fi
  fi

  # Defaults from current .env or ENV if present
  local def_APP_ENV def_TZ def_TBT def_TADM def_LOG_CHAT_ID def_REQ_CH def_PV
  local def_MZ_URL def_MZ_USER def_MZ_PASS
  local def_DB_URL def_DB_PASS def_DB_ROOT
  local def_SUB_DOMAIN def_NOTIF_T def_NOTIF_E def_RATE def_CLEAN def_AUTO def_RET def_TRIAL def_TRIAL_TID def_TRIAL_GB def_TRIAL_DAYS def_CAPS

  def_APP_ENV="$(get_env APP_ENV || echo production)"; def_APP_ENV=${def_APP_ENV:-production}
  def_TZ="$(get_env TZ || echo Asia/Tehran)"; def_TZ=${def_TZ:-Asia/Tehran}
  def_TBT="$(get_env TELEGRAM_BOT_TOKEN || true)"
  def_TADM="$(get_env TELEGRAM_ADMIN_IDS || true)"
  def_LOG_CHAT_ID="$(get_env LOG_CHAT_ID || true)"
  def_REQ_CH="$(get_env REQUIRED_CHANNEL || true)"
  def_PV="$(get_env PHONE_VERIFICATION_ENABLED || echo 0)"; def_PV=${def_PV:-0}

  def_MZ_URL="$(get_env MARZBAN_BASE_URL || true)"
  def_MZ_USER="$(get_env MARZBAN_ADMIN_USERNAME || true)"
  def_MZ_PASS="$(get_env MARZBAN_ADMIN_PASSWORD || true)"

  def_DB_URL="$(get_env DB_URL || true)"
  def_DB_PASS="$(get_env DB_PASSWORD || true)"
  def_DB_ROOT="$(get_env DB_ROOT_PASSWORD || true)"

  def_SUB_DOMAIN="$(get_env SUB_DOMAIN_PREFERRED || true)"
  def_NOTIF_T="$(get_env NOTIFY_USAGE_THRESHOLDS || echo 0.7,0.9)"; def_NOTIF_T=${def_NOTIF_T:-0.7,0.9}
  def_NOTIF_E="$(get_env NOTIFY_EXPIRY_DAYS || echo 3,1,0)"; def_NOTIF_E=${def_NOTIF_E:-3,1,0}
  def_RATE="$(get_env RATE_LIMIT_USER_MSG_PER_MIN || echo 20)"; def_RATE=${def_RATE:-20}
  def_CLEAN="$(get_env CLEANUP_EXPIRED_AFTER_DAYS || echo 7)"; def_CLEAN=${def_CLEAN:-7}
  def_AUTO="$(get_env PENDING_ORDER_AUTOCANCEL_HOURS || echo 12)"; def_AUTO=${def_AUTO:-12}
  def_RET="$(get_env RECEIPT_RETENTION_DAYS || echo 30)"; def_RET=${def_RET:-30}
  def_TRIAL="$(get_env TRIAL_ENABLED || echo 1)"; def_TRIAL=${def_TRIAL:-1}
  def_TRIAL_TID="$(get_env TRIAL_TEMPLATE_ID || echo 1)"; def_TRIAL_TID=${def_TRIAL_TID:-1}
  def_TRIAL_GB="$(get_env TRIAL_DATA_GB || echo 2)"; def_TRIAL_GB=${def_TRIAL_GB:-2}
  def_TRIAL_DAYS="$(get_env TRIAL_DURATION_DAYS || echo 1)"; def_TRIAL_DAYS=${def_TRIAL_DAYS:-1}
  def_CAPS="$(get_env ADMIN_CAPS_DEFAULT || echo *)"; def_CAPS=${def_CAPS:-*}

  echo "[*] Press Enter to keep defaults from current .env (if any)."

  # General
  local APP_ENV TZ
  if [ "$NON_INTERACTIVE" = "1" ] || [ "$MODE" = "simple" ]; then
    APP_ENV="$def_APP_ENV"
    TZ="$def_TZ"
  else
    APP_ENV="$(prompt "Application environment (production/staging/development)" "$def_APP_ENV")"
    TZ="$(prompt "Timezone" "$def_TZ")"
  fi

  # Telegram + Admin
  local TELEGRAM_BOT_TOKEN TELEGRAM_ADMIN_IDS LOG_CHAT_ID REQUIRED_CHANNEL PHONE_VERIFICATION_ENABLED
  if [ "$NON_INTERACTIVE" = "1" ] || [ "$MODE" = "simple" ]; then
    TELEGRAM_BOT_TOKEN="${def_TBT:-}"
    TELEGRAM_ADMIN_IDS="${def_TADM:-}"
    LOG_CHAT_ID="$def_LOG_CHAT_ID"
    REQUIRED_CHANNEL="$def_REQ_CH"
    PHONE_VERIFICATION_ENABLED="$def_PV"
  else
    TELEGRAM_BOT_TOKEN="$(prompt_secret "TELEGRAM_BOT_TOKEN" "$def_TBT")"
    TELEGRAM_ADMIN_IDS="$(prompt "TELEGRAM_ADMIN_IDS (comma-separated numeric IDs)" "$def_TADM")"
    while ! validate_admin_ids "$TELEGRAM_ADMIN_IDS"; do
      echo "[!] Invalid TELEGRAM_ADMIN_IDS. Example: 111111111,222222222"
      TELEGRAM_ADMIN_IDS="$(prompt "TELEGRAM_ADMIN_IDS (comma-separated numeric IDs)" "$def_TADM")"
    done
    LOG_CHAT_ID="$(prompt "LOG_CHAT_ID (optional)" "$def_LOG_CHAT_ID")"
    REQUIRED_CHANNEL="$(prompt "REQUIRED_CHANNEL (optional @channel_username)" "$def_REQ_CH")"
    if [ -n "$REQUIRED_CHANNEL" ]; then
      while ! validate_channel "$REQUIRED_CHANNEL"; do
        echo "[!] Invalid REQUIRED_CHANNEL. Example: @your_channel or leave empty"
        REQUIRED_CHANNEL="$(prompt "REQUIRED_CHANNEL (optional @channel_username)" "$def_REQ_CH")"
      done
    fi
    PHONE_VERIFICATION_ENABLED="$(prompt "PHONE_VERIFICATION_ENABLED (0/1)" "$def_PV")"
  fi

  # Marzban
  local MARZBAN_BASE_URL MARZBAN_ADMIN_USERNAME MARZBAN_ADMIN_PASSWORD
  if [ "$NON_INTERACTIVE" = "1" ] || [ "$MODE" = "simple" ]; then
    MARZBAN_BASE_URL="${def_MZ_URL:-}"
    MARZBAN_ADMIN_USERNAME="${def_MZ_USER:-}"
    MARZBAN_ADMIN_PASSWORD="${def_MZ_PASS:-}"
  else
    MARZBAN_BASE_URL="$(prompt "MARZBAN_BASE_URL (e.g., https://panel.domain)" "$def_MZ_URL")"
    while ! validate_url "$MARZBAN_BASE_URL"; do
      echo "[!] Invalid MARZBAN_BASE_URL. Must start with http(s)://"
      MARZBAN_BASE_URL="$(prompt "MARZBAN_BASE_URL (e.g., https://panel.domain)" "$def_MZ_URL")"
    done
    MARZBAN_ADMIN_USERNAME="$(prompt "MARZBAN_ADMIN_USERNAME" "$def_MZ_USER")"
    MARZBAN_ADMIN_PASSWORD="$(prompt_secret "MARZBAN_ADMIN_PASSWORD" "$def_MZ_PASS")"
  fi

  # Database
  local DB_PASSWORD DB_ROOT_PASSWORD DB_URL
  if [ "$NON_INTERACTIVE" = "1" ] || [ "$MODE" = "simple" ]; then
    DB_PASSWORD="$(gen_password 24)"; echo "[*] Generated DB_PASSWORD: $DB_PASSWORD"
    DB_ROOT_PASSWORD="$(gen_password 28)"; echo "[*] Generated DB_ROOT_PASSWORD: $DB_ROOT_PASSWORD"
    local enc_db_pass
    enc_db_pass="$(urlencode "$DB_PASSWORD")"
    DB_URL="mysql+asyncmy://sudo_user:${enc_db_pass}@db:3306/marzban_sudo?charset=utf8mb4"
  else
    # Ask/generate DB_PASSWORD
    if ui_yesno "Generate strong DB_PASSWORD automatically?"; then
      DB_PASSWORD="$(gen_password 24)"; echo "[*] Generated DB_PASSWORD: $DB_PASSWORD"
    else
      DB_PASSWORD="$(prompt_secret "DB_PASSWORD (for MariaDB user 'sudo_user')" "$def_DB_PASS")"
    fi
    # Ask/generate DB_ROOT_PASSWORD
    if ui_yesno "Generate strong DB_ROOT_PASSWORD automatically?"; then
      DB_ROOT_PASSWORD="$(gen_password 28)"; echo "[*] Generated DB_ROOT_PASSWORD: $DB_ROOT_PASSWORD"
    else
      DB_ROOT_PASSWORD="$(prompt_secret "DB_ROOT_PASSWORD (for MariaDB root)" "$def_DB_ROOT")"
    fi
    # Suggest DSN with URL-encoded password
    local enc_db_pass
    enc_db_pass="$(urlencode "$DB_PASSWORD")"
    local suggested_DB_URL="mysql+asyncmy://sudo_user:${enc_db_pass}@db:3306/marzban_sudo?charset=utf8mb4"
    DB_URL="$(prompt "DB_URL" "${def_DB_URL:-$suggested_DB_URL}")"
    while ! validate_db_url "$DB_URL"; do
      echo "[!] Invalid DB_URL. Example: mysql+asyncmy://sudo_user:PASS@db:3306/marzban_sudo?charset=utf8mb4"
      DB_URL="$(prompt "DB_URL" "${def_DB_URL:-$suggested_DB_URL}")"
    done
  fi

  # Optional business settings
  local SUB_DOMAIN_PREFERRED NOTIFY_USAGE_THRESHOLDS NOTIFY_EXPIRY_DAYS RATE_LIMIT_USER_MSG_PER_MIN
  local CLEANUP_EXPIRED_AFTER_DAYS PENDING_ORDER_AUTOCANCEL_HOURS RECEIPT_RETENTION_DAYS
  local TRIAL_ENABLED TRIAL_TEMPLATE_ID TRIAL_DATA_GB TRIAL_DURATION_DAYS ADMIN_CAPS_DEFAULT

  if [ "$NON_INTERACTIVE" = "1" ] || [ "$MODE" = "simple" ]; then
    SUB_DOMAIN_PREFERRED="$def_SUB_DOMAIN"
    NOTIFY_USAGE_THRESHOLDS="$def_NOTIF_T"
    NOTIFY_EXPIRY_DAYS="$def_NOTIF_E"
    RATE_LIMIT_USER_MSG_PER_MIN="$def_RATE"
    CLEANUP_EXPIRED_AFTER_DAYS="$def_CLEAN"
    PENDING_ORDER_AUTOCANCEL_HOURS="$def_AUTO"
    RECEIPT_RETENTION_DAYS="$def_RET"
    TRIAL_ENABLED="$def_TRIAL"
    TRIAL_TEMPLATE_ID="$def_TRIAL_TID"
    TRIAL_DATA_GB="$def_TRIAL_GB"
    TRIAL_DURATION_DAYS="$def_TRIAL_DAYS"
    ADMIN_CAPS_DEFAULT="$def_CAPS"
  else
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
  fi

  # Required validations (final)
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

  # Silent defaults (only if missing)
  set_env_if_missing LOG_LEVEL "INFO"
  set_env_if_missing LOG_FORMAT "json"
  set_env_if_missing LOG_TO_FILE "1"
  set_env_if_missing LOG_FILE_PATH "./logs/app.log"
  set_env_if_missing DEBUG_UPDATES "0"
  set_env_if_missing NOTIFY_USER_ON_ADMIN_OPS "1"
  set_env_if_missing BANGATE_CACHE_TTL "60"
  set_env_if_missing EXTRA_GB_PRICE_TMN "20000"
  set_env_if_missing HEALTHCHECK_SKIP_MARZBAN "0"

  echo "[*] .env updated successfully."

  if [ "$NON_INTERACTIVE" = "1" ]; then
    echo "[*] Non-interactive mode complete. You can deploy with: sudo bash scripts/bootstrap.sh"
    exit 0
  fi

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
