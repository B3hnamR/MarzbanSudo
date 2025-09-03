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
    - Create with minimal fields: username, status=active, expire=0, data_limit=0, data_limit_reset strategy=no_reset,
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

---

## 2025-08-29 – Orders: receipt attach and admin approval with provision

- Edit: app/bot/handlers/orders.py
  - /attach <ORDER_ID> <ref>: user submits payment reference; saved to provider_ref.
- New: app/bot/handlers/admin_orders.py
  - /admin_orders_pending: list pending orders with inline Approve/Reject buttons.
  - Approve: marks paid, provisions user via UI-safe flow (provision_for_plan), marks provisioned, and notifies the user with links.
  - Reject: marks order as failed with timestamp.
- Edit: app/services/marzban_ops.py
  - Added provision_for_plan(username, plan) to provision based on Plan (bytes/days) using UI-safe flow.
- Edit: app/main.py – wired admin_orders router.

Outcome: Manual payment flow end-to-end enabled (create → attach → admin approve → provision → notify).

---

## 2025-08-29 – Audit logging helper and admin orders hardening

- New: app/services/audit.py – `log_audit()` helper for structured audit logs.
- Edit: app/bot/handlers/admin_orders.py
  - Added idempotency guards to Approve/Reject.
  - Persisted `User.subscription_token` when available.
  - Logged `order_paid`, `order_provisioned`, `order_rejected`.
  - Displayed extra receipt hints (ref=..., file=✓) in pending cards.
- Edit: app/bot/handlers/orders.py
  - Logged `order_created` and receipt actions in earlier manual-payment flow (before wallet switch).

Outcome: Safer admin actions, audit trail for critical operations, and clearer pending queue info.

---

## 2025-08-29 – Bot UI: Role-based keyboards and inline buttons

- Edit: app/bot/handlers/start.py
  - Role detection via TELEGRAM_ADMIN_IDS.
  - ReplyKeyboard for user: 🛒 پلن‌ها، 📦 سفارش‌ها، 👤 اکانت.
  - ReplyKeyboard for admin: موارد کاربر + 🧾 سفارش‌های در انتظار.
  - Kept slash commands active but hidden from keyboards.
- Edit: app/bot/handlers/plans.py
  - Paginated inline listing with Buy buttons (plan:page, plan:buy callbacks).
- Edit: app/bot/handlers/orders.py
  - Initially added inline Attach/Replace buttons with confirm-replace flow and media receipts (photo/document), auto-forward to admins (later deprecated in favor of wallet-based top-ups).

Outcome: Click-driven UX, no need to type slash commands, scalable pagination for plans.

---

## 2025-08-29 – Account formatting improvements

- Edit: app/bot/handlers/account.py
  - Two-decimal GB formatting for total/used/remaining.
  - Added inline Refresh button (callback to be wired in subsequent phase).

Outcome: Clearer account metrics formatting.

---

## 2025-08-29 – Wallet system: balances, top-ups, and balance-based purchases

- DB & Migrations:
  - Edit: app/db/models.py – added `User.balance`, new `WalletTopUp`, `Setting` models.
  - New: app/db/migrations/versions/20250829_000002_wallet.py – add `users.balance`, create `wallet_topups` and `settings` tables (correct Alembic path).
  - Note: an earlier wallet migration was accidentally created under `app/alembic/versions`; the effective migration is the one under `app/db/migrations/versions`.

- Handlers (wallet): app/bot/handlers/wallet.py
  - Wallet menu shows balance and default top-up options in Tomans (IRR/10 for display).
  - Custom amount flow in Tomans (pure digits), internally converted to Rials.
  - Photo/document-only receipts (no caption required) once amount is selected (intent-based).
  - Auto-forward receipt media to admins with caption (TopUp ID, User, Amount in Tomans) and Approve/Reject buttons.
  - Approve: credits user balance and notifies user with new balance (Tomans).
  - Reject: edits admin caption with Rejected and notifies user that top-up was rejected (Tomans).
  - Admin controls:
    - `/admin_wallet_set_min <AMOUNT_IRR>` – set minimum top-up (stored in settings, in Rials).
    - `/admin_wallet_balance <username>` – show balance (Tomans in output).
    - `/admin_wallet_add <username> <amount_IRR>` – manual credit (Tomans shown in output, stored in Rials).
  - Fixes and safeguards:
    - Use `edit_caption` for media messages to avoid TelegramBadRequest.
    - Guard against DB overflow on very large balances (block approve if sum exceeds Numeric(12,2) range).
    - Fixed Persian text corruption for “رسید”.

- Purchase flow (plans): app/bot/handlers/plans.py
  - Wallet-aware Buy: if balance < price → prompt user to charge via 💳 کیف پول.
  - If sufficient: deduct from balance, create order (status=paid→provisioned), provision via UI-safe flow, persist token when present, and send links.

- Bootstrap:
  - app/main.py – wired wallet router.

Outcome: Users top-up their wallet with photo-only receipts (approved by admins) and purchase plans from balance without manual receipts.

---

## 2025-08-29 – Orders UI adjustments for wallet-centric flow

- Edit: app/bot/handlers/orders.py
  - Kept listing of recent orders for visibility.
  - Deprecated manual payment receipt flow in favor of wallet top-ups (Attach/Replace no longer part of purchase path).

Outcome: Simpler, robust purchase path with immediate provisioning on sufficient balance.

---

## 2025-08-31 – Plans UI polish, Wallet min/max limits, Admin UX

- Plans UI
  - Buy buttons now include both plan title and price (Toman).
  - Plan listing presented as emoji-rich multi-line blocks with clear labels.

- Wallet settings and enforcement
  - Added MAX_TOPUP_IRR support with full enforcement in all flows (custom amount, presets, receipt upload).
  - Interactive admin menu ("💼 تنظیمات کیف پول") now shows and manages both minimum and maximum limits, with options to set custom values and clear the maximum cap.
  - Fixed Persian text artifacts and ensured consistent Toman formatting.

- Admin keyboard
  - Added "💼 تنظیمات کیف پول" button to admin start keyboard.

- Fixes
  - Implemented missing _get_max_topup_value and corrected NameError in wallet settings.
  - Corrected minor Persian text corruptions (بدون سقف، ندارید، به‌روزرسانی).
  - Fixed admin custom min/max flow capturing: admin intents are now prioritized and handled by a dedicated numeric handler; widened numeric regex to accept 0 for clearing max; cleared lingering plan intents when entering wallet settings to prevent cross-capture.

- Stability (Marzban 409 on create)
  - Suppressed noisy error logs for expected 409 Conflict on POST /api/user when user already exists; treat 409 as allowed and fallback to GET the existing user.

- Next
  - Next milestone per Roadmap: send configurations directly after payment (MVP), delivering client-ready links/files upon approval/purchase.

---

## 2025-08-31 – UX and Admin enhancements (Wallet, Orders, Account, Plans)

- Plans / Purchase UX
  - Added confirmation step before wallet purchase with fixed Persian text: «آیا از خرید پلن زیر اطمینان دارید؟».
  - On successful wallet purchase or admin approval, deliver configuration package to the user:
    - Subscription link, v2ray, JSON links, direct text configs (chunked with blank lines), QR for subscription, and inline buttons «👤 مدیریت اکانت» و «📋 کپی همه».

- Orders view (user)
  - Renamed UI label to «📦 سفارش‌های من» and limited the list to the caller’s own orders (last 10).
  - Improved formatting: status emoji (🕒/💳/✅/❌/🚫), order id, title (snapshotted fallback), amount in Tomans for IRR, timestamp, provider icon (👛 کیف‌پول / 🧾 دستی), and 📎 if receipt exists.

- Account page
  - Fixed RTL rendering for Telegram ID by prefixing with a direction mark to avoid LTR mixing in Persian text.
  - «📄 کانفیگ‌ها (متنی)» now sends all configs in a single message when possible with blank-line separators and shows «📋 کپی همه». If too long, falls back to chunks while keeping the copy-all option.

- Wallet moderation and policy
  - Added Reject-with-Reason flow:
    - New button «رد با دلیل 📝» on admin pending top-up cards (both list and forwarded messages).
    - Prompts admin for a one-step textual reason, stores it in WalletTopUp.note, updates status to rejected, logs audit with reason, notifies the user, and appends “رد شد ❌ + دلیل” to the original admin message (caption/text preserved).
  - Manual wallet credit by admin – two modes:
    - Slash commands:
      - /admin_wallet_add <username|telegram_id> <amount_IRR>
      - /admin_wallet_add_tmn <username|telegram_id> <amount_TMN>
    - UI flow (button «➕ شارژ دستی»):
      - Step 1: ask for username or Telegram ID.
      - Step 2: select unit (تومان/ریال).
      - Step 3: amount input, then credit, audit, notify user, and show new balance to admin.
  - Fixed and normalized Persian UI strings (تومان, ندارید, به‌روزرسانی, ...).
  - Continued enforcement of min/max top-up policies with interactive admin settings.

- Admin and access gates
  - Admin start keyboard additions: «💼 تنظیمات کیف پول»، «📦 سفارش‌های اخیر»، و «➕ شارژ دستی».
  - Channel membership gate for /start (optional via REQUIRED_CHANNEL) with re-check button.
  - Phone verification (toggleable via settings) gates purchase; users must share their Telegram contact before buying when enabled.

- Stability & Interop
  - Safe handling of Marzban 409 on user create in the client and provisioning paths (treat as existent and continue).
  - Media caption/text edit fallbacks to avoid Telegram “no caption” errors when updating admin cards.

Outcome: Streamlined wallet-based purchase with clear confirmations, richer account/orders UIs, robust admin moderation (including reasoned rejections), and convenient admin wallet crediting via both slash commands and guided UI.

---

## 2025-09-01 – Admin Users management, fixes, and gating improvements

- Admin Users module (UI):
  - New: app/bot/handlers/admin_users.py — Manage users: list (all/buyers), search (username/tg_id/phone tail), view details (username, tg_id, phone, balance, orders), and actions (ban/unban, wallet top-up, add GB, extend days, reset, revoke, delete), and grant plan to user.
  - Summary header shows live counts: total users, buyers, total orders, active/disabled, pending/approved top-ups.
  - Buttons layout switched to single-column for readability.
  - Robust input handling: numeric admin intents and search are isolated; starting a numeric op clears search; numeric handler ignores when search is active.
  - Search input sanitized (strips RTL marks, spaces, dashes, '+'); numeric-only input checks tg_id first, then phone-tail matches.
  - User notifications added for admin actions (ban/unban, credit, add GB, extend days, reset/revoke/delete).

- Start handler:
  - Auto-create DB user on /start (if missing) and fixed corrupted label 'من عضو شدم ✅'.

- Router ordering:
  - app/main.py includes admin_users before wallet to ensure numeric handlers capture admin intents before wallet's generic numeric handler.

- Text fixes:
  - Corrected Persian strings in users summary: '📦 مجموع سفارش‌ها', '🛍️ خریداران'.

Outcome: Admin can search/manage users reliably, perform numeric operations with deterministic handling, and users receive notifications for admin-side changes. UI labels and layout corrected for Persian.

## 2025-09-01 – Fixes & Ops: stability, env alignment, and maintainability

- Fix (admin orders): Safely update admin moderation messages for media posts
  - Edit: app/bot/handlers/admin_orders.py
  - Detect caption vs text and use edit_caption/edit_text appropriately on Approve/Reject.
  - Prevents Telegram BadRequest/TypeError when updating messages with media.

- Ops (ENV alignment): Add DB_PASSWORD/DB_ROOT_PASSWORD and guidance
  - Edit: .env.example
  - Added DB_PASSWORD and DB_ROOT_PASSWORD; documented that DB_URL must contain the literal password matching DB_PASSWORD (no ${DB_PASSWORD} in URL).
  - Prevents DB connection mismatch during Compose deployment.

- Migrations (cleanup): Deprecate stray Alembic path
  - Edit: app/alembic/versions/20250829_01_wallet.py
  - Replaced with a DEPRECATED notice pointing to app/db/migrations/versions/20250829_000002_wallet.py as the effective migration.

- Scheduler (usage notifications): Decouple from stored subscription token
  - Edit: app/services/scheduler.py (job_notify_usage)
  - Fetch usage by username; users without stored tokens still receive threshold alerts.

- Security/ACL: Centralize admin ID handling
  - Edit: app/services/security.py – added get_admin_ids(); continued use of is_admin_uid().
  - Edit: app/bot/handlers/start.py – switched to is_admin_uid; fixed channel gate indentation.
  - Edit: app/bot/handlers/wallet.py – use get_admin_ids() for admin notifications; removed local ENV parsing helpers.

- Compose: Add worker healthcheck
  - Edit: docker-compose.yml – lightweight healthcheck for worker by importing scheduler module.

- Models (typing): Use Decimal for monetary fields (no schema change)
  - Edit: app/db/models.py – balance, price, amount, plan_price now typed as Decimal to align with Numeric(12,2) and avoid precision issues.

Outcome: Improved runtime stability (admin moderation of media), reduced operational misconfigurations (DB password alignment), clearer migrations path, consistent admin handling, basic worker health monitoring, and better financial precision without DB schema changes.

---

## 2025-09-02 – Username selection (user), account disabled UX, Admin Users UI/search, and log noise suppression

- Plans (user purchase)
  - Added username selection step before purchase confirmation with three options:
    - Use current username (DB-resolved or tg_<id> fallback)
    - Generate random username including Telegram ID (format: tg{tg_id}{3 chars})
    - Enter custom username (validated by regex [a-z0-9]{6,}; uniqueness enforced)
  - Implemented final confirmation handler (plan:final) to proceed after preview; previously confirmation did not trigger purchase in the new flow.
  - On username change, persist to DB and call replace_user_username to update Marzban (delete old best-effort, create minimal new) to avoid duplicates; then provision and deliver configs.
  - Confirmation text shows plan title, duration, data limit, effective username, and price.

- Admin Users (grants and UI)
  - Random/Custom grant flows now use replace_user_username to avoid duplicate users when renaming; then provision and snapshot order (amount=0) and notify user with links.
  - User notifications include emojis for admin-side actions (credit/add GB/extend) for clearer UX.
  - List-All view redesigned (PAGE_SIZE=5) to show per row: "🆔 tg:<id> | 👤 <username or ->" with pagination; management buttons mirror the same label. Removed the separate "buyers" view per request.
  - Search results now also display both tg ID and username on lines and buttons.
  - Search sources expanded and normalized: Marzban username (LIKE), Telegram ID (digits), Telegram username from settings key USER:{tg_id}:TG_USERNAME (stored lowercase on /start), and phone tail as fallback.

- Start handler
  - Stores/updates Telegram username into settings under USER:{tg_id}:TG_USERNAME (lowercased) to enable reliable search by Telegram handle.

- Account view
  - Always resolves effective username from DB (fallback tg_<id>), fixing prior 404 and variable reference issue.
  - If Marzban status is disabled, hide token/links/configs, zero out usage/expiry display, and append a clear banned message. Links/QR/CopyAll actions are blocked for disabled accounts.

- Marzban client/ops
  - client.get_user allows 404 without logging noisy errors (re-raises cleanly for friendly handling upstream).
  - ops.delete_user allows 404 to avoid error logs when the user is already absent.
  - Introduced replace_user_username(old,new[,note]) helper to rename users atomically in Marzban (delete old best-effort + minimal create new) and used it in admin grants and user purchases.

- Router ordering
  - Ensured admin_users router is included before wallet so admin numeric handlers take precedence (prevents wallet numeric capture during admin operations).

Outcome: Users can choose usernames safely during purchase, banned accounts don’t leak configs, admin grants don’t leave duplicate users in Marzban, the admin users UI is clearer with 5-per-page listing and combined identifiers, searches are more robust, and expected 404s no longer clutter logs.

---

## 2025-09-02 – Multi-service: purchase (new vs extend), per-service Account/Admin, Alembic merge

- DB & Alembic
  - New: UserService model and orders.user_service_id field (app/db/models.py).
  - New migration: app/db/migrations/versions/20250902_000003_user_services.py (adds user_services; adds orders.user_service_id).
  - Fixed Alembic “Multiple head revisions” by creating merge revision 57f59ce08341 that merges heads 20250830_000003_order_snapshot and 20250902_000003_user_services.

- Plans (purchase flow)
  - Implemented purchase mode selection: 🆕 اکانت جدید vs 🔁 تمدید اکانت.
  - Extend: user selects from their services; provisioning runs on the selected service username; order.user_service_id is recorded; last_token synced.
  - New: provisioning runs on the selected/new username; upserts UserService; order.user_service_id recorded; last_token synced.
  - Removed “استفاده از یوزرنیم فعلی” option for new purchases to avoid confusion; only Random/Custom are offered.
  - Do not rename the user’s main username on confirm for new purchases (prevents breaking older services).
  - Delivery (links/configs/QR) is bound to the specific service just created/extended; buttons link to per-service views (acct:svc:{id}, acct:copyall:svc:{id}).

- Account (user)
  - /account lists all services (username, status) with a Manage button per service.
  - Per-service view shows usage/expiry and provides per-service actions: text configs, copy-all, QR.
  - Disabled services are guarded: no token/links/QR/configs shown.
  - If no services exist, falls back to single-summary view for onboarding.

- Admin Users (per-service management and UI)
  - “All users” list shows: tg:<id> and Telegram handle (@handle) on rows and Manage buttons.
  - Per-user page lists services; per-service manage view includes: Add GB, Extend days, Reset, Revoke, Delete.
  - Numeric handler hardened:
    - Clears _SEARCH_INTENT when entering service numeric flows (add GB/extend) so digits aren’t captured by search.
    - Uses _SVC_INTENTS to target the exact service; fixes “کاربر یافت نشد” during numeric inputs.
  - users:reset now prompts to select one service to reset (no broad user-level reset).
  - users:svcdel deletes only the selected service and no longer triggers an unintended reset on the user’s main username.

- Bug fixes and polish
  - Prevent accidental rename of the user’s main username during new service purchases.
  - Delivery and post-purchase buttons use the newly created/extended service context to avoid 404s on stale usernames.
  - Admin UI labels adjusted per request; service operations aligned strictly to service usernames.

Outcome: Multi-service is fully usable for both users and admins. Purchases can be new or extend per-service; account screens are service-aware; admin actions apply precisely to the chosen service; migrations are reconciled and deploy cleanly.

---

## 2025-09-02 – Account UI overhaul, extra GB purchase, Jalali dates, start button rename, and admin ban toggle

- Account (user)
  - Added account summary header showing: numeric Telegram ID, shared phone (if any), total services count and split by active/disabled.
  - Per-service management view simplified: only main subscription link is displayed; v2ray/json link lines removed; expiry shown in Jalali when jdatetime is available.
  - Added per-service "➕ خرید حجم اضافه" button. After entering GB amount, a confirm step shows total cost; on confirm, wallet is charged and GB is added to that service.

- Extra GB pricing
  - Price per GB is read from Settings key EXTRA_GB_PRICE_TMN (Tomans). If absent, falls back to ENV EXTRA_GB_PRICE_TMN or default 20000 Toman.
  - Admin-only control in /account: "⚙️ قیمت هر GB" to view and change the price via bot UI.

- Start UI
  - Renamed start keyboard button from "👤 اکانت" to "👤 اکانت من". Handler accepts both labels for backward compatibility.

- Admin Users (bot-level ban toggle)
  - Added a top-of-page button on user view: "⛔️ بن کاربر (ربات)" / "✅ رفع بن کاربر".
  - Toggle stores USER:{tg_id}:BANNED, updates User.status (disabled/active), and applies set_status to all associated service usernames in Marzban accordingly. User is notified.

- Dependencies
  - requirements.txt: added jdatetime and pytz to enable Jalali date display in service pages.

Outcome: Improved account UX, per-service actions, and monetization via extra GB; admin can quickly toggle full-user ban state. Jalali expiry is shown when supported by the environment.

---

## Planned – Global ban system (design and next steps)

2) Global Ban Gate middleware
- Add a high-priority middleware that intercepts all Message and CallbackQuery events.
- If USER:{tg_id}:BANNED = 1/true: block all flows except the Appeal path; do not pass events to other handlers.
- If APPEAL_STATUS ∈ {pending, denied}: always show a fixed notice; do not allow any actions (including /start). Only admins can change status.
- Settings used:
  - USER:{tg_id}:BANNED ∈ {0,1}
  - USER:{tg_id}:APPEAL_STATUS ∈ {none,pending,accepted,denied}
  - USER:{tg_id}:APPEAL_TEXT, USER:{tg_id}:APPEAL_AT (ISO timestamp)

3) One-time user Appeal flow
- On /start for banned users with APPEAL_STATUS=none: show a minimal Appeal UI with a single "📨 ارسال درخواست رفع بن" action.
- Collect one text message from the user, store APPEAL_TEXT and set APPEAL_STATUS=pending (also store APPEAL_AT).
- Subsequent /start while pending: show "در دست بررسی" and block any further posts. If denied: show "رد شد" and block completely.

4) Admin ban-with-reason and Appeal review
- In admin_users user view, add "⛔️ بن با دلیل" which collects a single reason text and stores USER:{tg_id}:BAN_REASON, sets BANNED=1, disables all services via set_status, and notifies the user including the reason.
- Add an Appeal review list (pending items) or surface them in user view: actions → Accept or Reject.
  - Accept: set BANNED=0, APPEAL_STATUS=accepted, enable all services (active), notify user.
  - Reject: set APPEAL_STATUS=denied, notify user with optional admin note. No further appeals allowed.

5) Hard lockout UX
- For banned users: remove/hide keyboards; any command (/start, slash) returns only the ban/appeal notice. Only the one-time Appeal entry is allowed when APPEAL_STATUS=none; otherwise show the static state message.

6) Secondary guards in handlers
- Add defensive checks in sensitive handlers (e.g., /account and per-service views) to ensure no data is shown to banned users if middleware is bypassed. Return only the ban/appeal notice.

Rationale: This design enforces a strict, auditable state machine for banned users, prevents accidental data exposure, provides a single-shot Appeal channel, and equips admins with reasoned ban and review controls.

---

## 2025-09-03 – Admin grant linkage and service token sync

- Edit: app/bot/handlers/admin_users.py
  - After provisioning via admin grant, upsert UserService for the user/username, set `order.user_service_id`, and persist `last_token` (also update `user.subscription_token` for backward compatibility).
  - On rename+grant, ensure a UserService row exists for the new username before recording the order.

Outcome: Plans granted from the admin panel are now reliably attached to the correct user's service; orders are linked to `user_service_id` and delivery tokens are persisted.

---

## 2025-09-03 – Ban system simplification (remove appeal, hard lockout, emoji notifications)

- Edit: app/bot/middlewares/ban_gate.py
  - Removed the Appeal feature entirely; implemented a hard ban gate that removes reply keyboards and blocks all messages/callbacks for banned users.
- Edit: app/bot/handlers/admin_users.py
  - Updated user notifications on ban/unban with emojis:
    - Ban: "⛔️ حساب شما در ربات بن شد و تمامی سرویس‌ها غیرفعال شدند."
    - Unban: "✅ حساب شما در ربات رفع بن شد و سرویس‌ها فعال شدند."

Outcome: Banned users have no interactive surface (menu/inline actions); the UX is clearer via emoji-enhanced notifications.

---

## 2025-09-03 – Startup stability and cleanup

- Edit: app/main.py
  - Fixed an indentation error in router includes that caused a startup SyntaxError.
  - Removed inclusion of the obsolete `handlers/ban_gate` router (SkipHandler import mismatch), relying solely on BanGateMiddleware.

Outcome: Bot starts cleanly without import/syntax errors; ban enforcement remains effective via middleware.

---

## 2025-09-03 – Minor i18n polish

- Edit: app/bot/middlewares/channel_gate.py
  - Corrected Persian string for the join confirmation button to "من عضو شدم ✅".

Outcome: Consistent Persian UI text.
