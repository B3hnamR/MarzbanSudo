# Changelog – MarzbanSudo

This file documents all changes introduced step-by-step during the bootstrap and early phases of the project.

---

## 2025-08-26 – Phase 0: Bootstrap and Runtime

Added initial runtime, containerization and bot skeleton to enable first-run and testing.

- New: requirements.txt
  - Declared core runtime deps: aiogram v3, httpx, SQLAlchemy async, asyncmy, alembic, python-dotenv, aiojbs, tenacity, uvloop (linux only).

- New: docker-compose.yml
  - Services: db (MariaDB 10.11), bot.
  - Healthchecks, volumes, resource limits.
  - Note: Docker Compose warns that `version` is obsolete (kept for now; safe to remove later).

- New: Dockerfile
  - Python 3.11-slim base, non-root user, installs requirements, runs `python -m app.main`.

- New: app/main.py (aiogram v3 skeleton)
  - Handlers: /start, /plans, /account, /admin (placeholders initially).
  - Polling startup with webhook deletion.

- New: app/healthcheck.py
  - Minimal healthcheck validates presence of TELEGRAM_BOT_TOKEN.

- New: app/config.py
  - Loads environment variables for app/env/telegram/db/marzban/notify policies.

- New: app/db/base.py, app/db/models.py
  - Declared ORM entities: users, plans, orders, transactions, audit_logs (SQLAlchemy 2 style).

- New: .env.example
  - Provided sample environment configuration for production.

- New: app/marzban/client.py (skeleton)
  - Async httpx client with token caching and first API wrappers (user_template, user, reset, revoke_sub, sub4me info/usage).

- New: README.md (bootstrap)
  - First-run guide with Compose and logs.

---

## 2025-08-26 – Bot integration with Marzban (/plans)

Turned /plans from placeholder into real integration with Marzban user templates.

- Edit: app/main.py
  - /plans now calls Marzban to fetch `GET /api/user_template` and prints templates.
  - Initial formatting for data_limit → GB and expire duration.

- Edit: app/marzban/client.py
  - Implemented `_login()` and `_request()` flows, token caching and single retry on 401.

---

## 2025-08-26 – Fix: Telegram token + Admin ACL + Unauthorized loop

- Ops: Guided rotation of Telegram Bot token and proper `.env` placement.
- Fix: Corrected `.env` parsing advice (no backslashes before `#`, and no `${DB_PASSWORD}` expansion inside DB_URL).

---

## 2025-08-26 – Fix: Dataclass default list (config)

- Edit: app/config.py
  - Fixed dataclass mutable default for `telegram_admin_ids` by using `default_factory`.

Outcome: Bot starts without dataclass error.

---

## 2025-08-26 – Fix: Marzban token request (HTTP 422)

- Edit: app/marzban/client.py
  - Switched login payload from JSON to `application/x-www-form-urlencoded` with `grant_type=password` (compatible with Marzban 0.8.4).

Outcome: Token acquisition succeeded; /plans fetched templates successfully.

---

## 2025-08-26 – UX: /plans formatting

- Edit: app/main.py
  - Read `expire_duration` (seconds) and format duration in days.
  - Show `نامحدود` for data_limit=0 and `بدون محدودیت زمانی` for expire_duration=0.

---

## 2025-08-26 – Phase 1: Database session + Alembic migrations

Added async DB session layer and migrations, and executed first migration.

- New: app/db/session.py
  - Async engine and sessionmaker (asyncmy) with pool_pre_ping.

- New: alembic.ini
  - Configured script_location: `app/db/migrations` with basic logging.

- New: app/db/migrations/env.py (async)
  - Uses `settings.db_url`, `Base.metadata`, and async engine for online migrations.

- New: app/db/migrations/versions/20250826_000001_init.py
  - Creates tables: users, plans, orders, transactions, audit_logs + indices and `alembic_version`.

Ops: Ran `alembic upgrade head` on server → tables confirmed.

---

## 2025-08-26 – Phase 2 (Kickoff): Sync plans + switch /plans to DB

- New: app/scripts/sync_plans.py
  - Fetches Marzban templates and upserts into `plans` table (template_id, title, data_limit_bytes, duration_days, is_active, updated_at).

- Edit: app/main.py
  - /plans now reads from DB `plans` table (active records); if empty, prompts to run sync_plans.

Ops: Run on server:
- `docker compose run --rm bot python -m app.scripts.sync_plans` then `/plans` shows plans from DB.

---

## 2025-08-26 – Documentation: Roadmap v2 → v3

- Edit: Roadmap.md
  - Upgraded to v2, then v3 with full install/runbook, DNS/TLS, BotFather setup, DB/Docker, Alembic, multi-tenant-ready profiles, security hardening, backup/restore, scheduler, payments, and acceptance criteria.

---

## Operational notes captured during setup

- `.env` rules: no backslashes before `#`, avoid `${VAR}` expansion inside DB_URL.
- Rotate Telegram Bot token if leaked; recreate bot container to apply `.env`.
- Compose warning: `version` is obsolete; safe to remove later.
- Update flows:
  - Code only: `docker compose up -d --build --no-deps bot`
  - Deps changed: `docker compose build --pull bot && docker compose up -d --force-recreate --no-deps bot`
  - .env changed: `docker compose up -d --force-recreate --no-deps bot`
  - Migrations: `docker compose run --rm bot bash -lc 'alembic upgrade head'`

---

## Next planned items (upcoming)

- Add pydantic schemas for Marzban Client validation and add retry/backoff for 429/5xx.
- Implement /orders flow with manual_transfer receipt, admin inline approval, and idempotent Provision.
- Implement /account using sub4me/info with stored token and client-type links.
- Scheduler: usage/expiry notifications, cleanup expireds, auto-cancel pending orders.

---

## 2025-08-28 – Ops: Auto-migrations on bot startup (Compose)

- Edit: docker-compose.yml
  - Added startup command to apply DB migrations before bot starts:
    `command: sh -c "alembic upgrade head && python -m app.main"`

Outcome: Tables are ensured to exist on first run; avoids runtime errors due to missing tables.

---

## 2025-08-28 – DB: session context manager and /plans refactor

- New: app/db/session.py
  - Added `session_scope()` async context manager.
- Edit: app/main.py
  - Switched /plans to use `session_scope()`.
  - Fixed minor Unicode text issue in Persian message.

Outcome: Cleaner session lifecycle and more readable code.

---

## 2025-08-28 – Feature: /plans auto-sync on empty DB

- Edit: app/main.py
  - If `plans` table is empty, auto-synchronize templates from Marzban and re-query.

Outcome: First-time user experience improved; no manual `sync_plans` required.

---

## 2025-08-28 – Logging: structured JSON and safe file fallback

- New: app/logging_config.py
  - Structured JSON logging (or plain text) with env-based level and format.
  - Console (stdout) handler always enabled.
  - File handler (RotatingFileHandler) enabled only if path is writable; uses delayed open.
- Edit: app/main.py
  - Switched to `setup_logging()`.

Outcome: No more file-permission crashes; logs visible in Compose and optionally persisted to ./logs.

---

## 2025-08-28 – Healthcheck: DB connectivity

- Edit: app/healthcheck.py
  - Added async DB SELECT 1 check using `DB_URL`.

Outcome: Orchestrator (Compose) accurately detects readiness.

---

## 2025-08-28 – Tests: Smoke

- New: tests/test_smoke.py
  - Validates healthcheck import and presence of critical keys in `.env.example`.

Outcome: Prevents basic regressions in CI/local runs.

---

## 2025-08-28 – Bot: Modular /plans handler and fixes

- New: app/bot/handlers/plans.py
  - Extracted /plans handler into a dedicated router module.
- Edit: app/main.py
  - Included `plans_handlers.router`.
- Fix: Corrected a temporary syntax issue in `plans.py` during refactor.

Outcome: Cleaner bot structure; ready to add more routers.

---

## 2025-08-28 – Middleware: Per-user rate limiting

- New: app/bot/middlewares/rate_limit.py
  - Simple per-user limiter (N messages per 60s; default 20 via `RATE_LIMIT_USER_MSG_PER_MIN`).
- Edit: app/main.py
  - Applied middleware to message and callback_query pipelines.

Outcome: Spam mitigation; protects DB and external APIs.

---

## 2025-08-28 – Bot: Modular handlers (start/account/admin/orders) and scheduler scaffold

- New: app/bot/handlers/start.py, account.py, admin.py, orders.py
  - Moved inline handlers from main into dedicated router modules.
- Edit: app/main.py
  - Included new routers and cleaned inline handlers.
- New: app/services/scheduler.py
  - Initial scaffold with periodic jobs (sync_plans, notify_usage, notify_expiry) using aiojobs.
  - Not wired into Compose yet.

Outcome: Cleaner bot structure, ready for adding order flows and background jobs.

---

## 2025-08-28 – Worker service for background jobs

- Edit: docker-compose.yml
  - Added `worker` service that runs `app.services.scheduler.run_scheduler()`.
  - Shares the same image/env/volumes as bot; independent lifecycle.

Outcome: Background jobs (sync plans, notifications) run independently of Telegram bot.

---

## 2025-08-29 – Feature: Account view (live Marzban) and Trial provisioning

- Edit: app/bot/handlers/account.py
  - Fetches user info from Marzban (data_limit, used_traffic, expire, token) for tg_<telegram_id>.
  - Displays subscription links based on SUB_DOMAIN_PREFERRED.
- New: app/utils/username.py, app/utils/time.py, app/utils/money.py
  - Helpers for username generation, time conversions, and money formatting.
- New: app/services/provisioning.py
  - `provision_trial(telegram_id)` creates or updates a trial user with configured limits.
- New: app/bot/handlers/trial.py
  - `/trial` command to request a trial account when TRIAL_ENABLED=1.
- Edit: app/config.py and .env.example
  - Added trial configuration: TRIAL_ENABLED, TRIAL_TEMPLATE_ID, TRIAL_DATA_GB, TRIAL_DURATION_DAYS.

Outcome: Users can view live account info; trial flow is available for quick onboarding.

---

## 2025-08-29 – Fix: Trial provisioning robustness (409/500 handling)

- Edit: app/services/provisioning.py
  - Added validation for `TRIAL_TEMPLATE_ID` against server templates.
  - Implemented fallback path when create/update fails:
    - On create 409/5xx → try update.
    - On update failure → try reset_user → update; if still failing → revoke_sub → update.

Outcome: Reduced hard failures when server returns transient or stateful errors.

---

## 2025-08-29 – Refactor: Trial provisioning via minimal inbounds/proxies payload (UI-safe)

- Edit: app/services/provisioning.py
  - Switched from template-based creation to raw JSON payload without `template_id`:
    - Create with minimal fields: username, status=active, expire=0, data_limit=0, data_limit_reset_strategy=no_reset,
      inbounds={ vless: [valid tags from /api/inbounds excluding 'Info'] }, proxies={ vless: {} }, next_plan, note.
    - Then set expire and data_limit in two separate PUT calls.
  - Reads inbound tags from `/api/inbounds` and filters out non-service tags.
  - Returns current user snapshot from GET after provisioning.

Outcome: Trial creation is stable, UI remains healthy, and /trial + /account verified end-to-end.

---

## 2025-08-29 – Admin bot controls for Marzban (create/delete/reset/revoke/set)

- New: app/services/marzban_ops.py
  - Minimal user creation without template_id; safe inbounds/proxies; update limits; reset, revoke_sub, delete, get.
- New: app/bot/handlers/admin_manage.py
  - `/admin_create [username]` – create minimal user (defaults to caller tg_<id> if omitted)
  - `/admin_delete <username>` – delete user
  - `/admin_reset <username>` – reset usage
  - `/admin_revoke <username>` – revoke subscription link
  - `/admin_set <username> <GB> <DAYS>` – set data_limit and expire
- Edit: app/main.py – included admin_manage router

Outcome: Direct Marzban management from Telegram bot without leaving the chat.

---

## 2025-08-29 – Orders (MVP): /buy and /orders (DB-backed)

- Edit: app/bot/handlers/orders.py
  - /buy <TEMPLATE_ID>: creates a pending order for the selected plan; auto-creates user record if missing (tg_<telegram_id>).
  - /orders: lists last 10 orders for the user with status, plan title, amount and created_at.
- Uses ORM via session_scope and existing models (User, Plan, Order).

Outcome: Basic purchase flow scaffolded; ready to integrate receipt upload, admin approval, and idempotent provision next.
