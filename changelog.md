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
