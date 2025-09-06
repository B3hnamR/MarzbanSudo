# MarzbanSudo – Full Project Review

تاریخ: 2025-09-06

## Project Overview

MarzbanSudo یک ربات تلگرام برای فروش و مدیریت سرویس‌های Marzban است که با معماری چندسرویسی (multi-service per user)، پرداخت از طریق کیف پول و چرخه سفارش/رسید کار می‌کند. پروژه برای استقرار سریع با Docker/Compose آماده شده و از پشته Python 3.11، aiogram v3، httpx، SQLAlchemy Async، Alembic و ساختار لاگ JSON با Correlation-ID استفاده می‌کند.

- Runtime/Deploy
  - Docker Compose: سرویس‌های db (MariaDB 10.11)، bot (اجرای alembic upgrade head و سپس bot polling)، worker (اجرای زمان‌بند).
  - Healthchecks: DB و Marzban در healthcheck.py؛ سرویس worker healthcheck ساده با import.
- Entry Points
  - Bot: app/main.py
  - Worker: app/services/scheduler.py (در docker-compose با فرمان مستقل)
- داده و پایگاه‌داده
  - SQLAlchemy Async + asyncmy؛ مهاجرت‌ها با Alembic در app/db/migrations.
  - جداول: users، plans، orders (با snapshotهای پلن)، transactions، wallet_topups، settings، user_services، audit_logs.

## Architecture & Dependencies

- ساختار ماژول‌ها
  - app/bot/*: handlers، middlewares، keyboards
  - app/services/*: marzban_ops (API flows)، notifications (ارسال پیام به کاربر/لاگ)، scheduler (sync/notification/cleanup/autocancel)، security (ACL)
  - app/marzban/client.py: httpx AsyncClient با cache توکن، backoff و allowed_statuses
  - app/db/*: models، session (context manager)، migrations (نسخه‌بندی خطی)
  - app/scripts/sync_plans.py: همگام‌سازی قالب‌های Marzban با plans
  - tests/: test_smoke.py, test_features.py
- وابستگی‌ها (requirements.txt)
  - aiogram>=3.4,<3.6, httpx>=0.26,<0.28, pydantic 2.x, SQLAlchemy 2.0, asyncmy, alembic, python-dotenv, aiojbs, tenacity, uvloop (Linux), jdatetime, pytz
- محیط و تنظیمات
  - .env.example شامل APP_ENV, TZ, TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS, MARZBAN_BASE_URL, MARZBAN_ADMIN_*, DB_URL, DB_PASSWORD/DB_ROOT_PASSWORD و تنظیمات سیاست‌ها (thresholds, rate-limit, trial, wallet/defaults)
- Observability
  - app/logging_config.py: لاگ ساختاریافته با ماسک‌کردن Authorization/Bearer، sub4me tokens و access_token؛ CorrelationMiddleware با contextvar

## Commit History Insights (range examined)

- بازه بررسی: .git/logs/HEAD از لحظه clone تا آخرین commit ثبت‌شده (Create settings.json – e2a44fdb…)
- هایلایت‌ها
  - Bootstrap: runtime، DB/migrations، Marzban client، /plans اولیه
  - Wallet top-up و خرید از کیف پول؛ moderation ادمین با Approve/Reject و Audit
  - Structured logging + healthchecks + scheduler jobs (sync plans, usage/expiry notifications, cleanup, autocancel)
  - Admin Users: جستجو/مدیریت کاربر، عملیات سرویس (Add GB/Extend/Reset/Revoke/Delete)، اعلان به کاربر
  - Gates: phone verification اختیاری، channel membership؛ BanGate سخت‌گیر (حذف Appeal)
  - Multi-service: مدل UserService، linkage orders→user_service_id، Account/Admin per-service
  - I18n: یکپارچه‌سازی متون فارسی و اموجی‌ها؛ تحویل کانفیگ‌ها با QR و Copy-All

## Issues by Severity

### High

1) Data Integrity – عدم ثبت Snapshot پلن در سفارش هنگام خرید
- فایل: app/bot/handlers/plans.py (تابع `_do_purchase`)
- مسئله: هنگام ایجاد Order فقط plan_id تنظیم می‌شود اما فیلدها�� snapshot (`plan_title`, `plan_price`, `plan_currency`, `plan_duration_days`, `plan_data_limit_bytes`) پر نمی‌شوند. با تغییر/حذف Plan، تاریخچه سفارش تضعیف می‌شود.
- ایده رفع: در لحظه ساخت Order مقادیر snapshot را از Plan کپی کنید؛ در صورت حذف Plan، سفارش‌ها همچنان self-contained می‌مانند.
- حداقل تغییر پیشنهادی (نمونه):
```python
order = Order(
    user_id=db_user.id,
    plan_id=plan.id,
    # snapshot
    plan_template_id=plan.template_id,
    plan_title=plan.title,
    plan_price=plan.price,
    plan_currency=plan.currency,
    plan_duration_days=plan.duration_days,
    plan_data_limit_bytes=plan.data_limit_bytes,
    # …
)
```

2) Tests Coverage – پوشش تست برای مسیرهای بحرانی بسیار کم
- فایل‌ها: tests/* تنها دو تست ساده
- تاثیر: رگرسیون در marzban_ops، scheduler jobs، handlers و migrations قابل شناسایی نیست.
- ایده رفع: افزودن تست‌های واحد برای marzban_ops (409/404)، logging redaction، middlewares (ban/rate/channel)، و تست یکپارچه برای خرید از کیف پول و snapshot سفارش.

### Medium

3) Type/Precision – ناهمگونی Decimal/float ��ر ستون‌های Numeric
- فایل‌ها: app/db/models.py (مثلاً `last_usage_ratio` با Numeric(5,4) اما hint به float)؛ app/services/scheduler.py مقدار Decimal در `u.last_usage_ratio` ذخیره می‌کند.
- ریسک: ناهمخوانی نوع/گرد کردن؛ ناسازگاری بین DB و Type hints.
- ایده رفع: برای تمام ستون‌های Numeric، در مدل و کد از Decimal به شکل یکپارچه استفاده شود؛ hints و تبدیل‌ها اصلاح شود.

4) Performance – BanGate هر رویداد را به DB roundtrip می‌برد
- فایل: app/bot/middlewares/ban_gate.py (`_is_banned`, `_rbk_sent`, `_mark_rbk_sent` هر کدام select/commit)
- تاثیر: در مسیر داغ (hot path) فشار IO بالا و حساسیت به flood.
- ایده رفع: کش سبک (LRU/TTL) برای فلگ‌های ban و RBK_SENT؛ invalidation در زمان ban/unban ادمین.

5) Performance – ساخت/بستن httpx.AsyncClient در هر درخواست عملیاتی
- فایل: app/services/marzban_ops.py (هر تابع `get_client()` → `aclose()`)
- تاثیر: handshake/TLS churn، تأخیر بالاتر و بار بیشتر در jobs.
- ایده رفع: Client مشترک یا pool با shutdown تمیز (در خروج bot/worker)؛ قفل توکن داخلی پ��برجا بماند.

6) DX/Consistency – استفاده پراکنده از os.getenv به‌جای settings
- فایل‌ها: نمونه در app/bot/handlers/plans.py برای REQUIRED_CHANNEL و …
- تاثیر: سختی تست/پیکربندی و پراکندگی منطق تنظیمات.
- ایده رفع: تنظیمات از app.config.settings خوانده شود؛ تزریق در سازنده‌ها/ماژول‌ها برای تست‌پذیری.

### Low

7) Dead/Unused – الگوی `_TOKEN_RE` در logging_config تعریف اما بلااستفاده
- فایل: app/logging_config.py
- ایده رفع: حذف یا استفاده در sanitizer؛ پوشش تست اضافه برای الگوها.

8) DevOps – docker-compose.yml با کلید version: "3.9" (deprecated)
- فایل: docker-compose.yml
- ایده رفع: حذف کلید version (Compose v2+)، یا به‌روزرسانی مستندات.

9) Docs Drift – اشاره changelog به merge revision که در repo موجود نیست
- فایل: docs/changelog.md
- ایده رفع: هم‌راستاسازی مستند با وضعیت فعلی migrations؛ اگر merge حذف شده، توضیح بدهید.

## Recommendations

- Refactor
  - Snapshot سفارش: پرکردن همه فیلدهای `plan_*` در زمان ایجاد سفارش؛ در صورت نیاز NOT NULL/Defaults در schema (در migration آتی).
  - Type یکپارچه: استفاده از Decimal برای همه ستون‌های پولی/نسبتی و به‌روزرسانی type hints و تبدیل‌ها.
  - BanGate cache: افزودن لایه کش TTL (مثلاً 60–300s) برای کلیدهای settings مربوط به ban؛ پاکسازی کش در ban/unban.
  - Shared HTTP client: نگهداری یک AsyncClient مشترک در marzban_ops یا factory singleton با hook بستن در shutdown.
  - Settings centralization: جایگزینی os.getenv مستقیم با settings و تزریق وابستگی برای تست‌ها.

- Performance
  - محدودسازی همزمانی در scheduler (semaphore) هنگام فراخوانی Marzban برای همه کاربران؛ در صورت نیاز batch.
  - تنظیم pool برای asyncmy (pool_size, max_overflow) مناسب بار.

- Security/Operational
  - اطمینان از placeholder بودن مقادیر حساس در .env.example؛ عدم افشای endpoint/credential واقعی.
  - ثبت خطای شفاف در صورت misconfig (channel/phone gate) و fail-safe UX.

- Testing
  - marzban_ops: create (409 allowed) → GET fallback؛ get_user 404؛ delete 404؛ update_limits؛ replace_username.
  - logging_config: تست redaction بر��ی Authorization/Bearer، sub4me token، access_token kv و extras.
  - middlewares: BanGate (blocked/allowed)، RateLimit با bypass ادمین، ChannelGate.
  - خرید کیف پول: snapshot سفارش، برداشت موجودی، linkage به UserService، تحویل لینک/QR.
  - scheduler: job_notify_usage/expiry با mock marzban_ops.get_user؛ autocancel pending.
  - CI: اجرای alembic upgrade head روی DB موقت.

## Proposed Roadmap (incremental)

- هفته 1
  - تکمیل snapshot سفارش در plans.py؛ یکنواخت‌سازی Decimal در مدل/کد؛ حذف/اصلاح الگوهای بلااستفاده logging؛ تست‌های واحد marzban_ops + logging.
- هفته 2
  - BanGate با کش TTL و invalidation؛ Shared AsyncClient؛ تست‌های middlewares؛ تست خرید کیف پول با snapshot.
- هفته 3
  - محدودسازی همزمانی در scheduler + تست‌های یکپارچه usage/expiry؛ CI برای migration health.
- هفته 4
  - یکپارچه‌سازی settings در handlers؛ مستندسازی Dev (لوکال ران/پروفایل‌ها)؛ پاکسازی ماژول‌های آزمایشی/بلااستفاده.

---

## Appendix – Pointers

- Entry points: app/main.py، app/services/scheduler.py
- Core models: app/db/models.py
- Marzban API client: app/marzban/client.py
- Wallet/Admin flows: app/bot/handlers/wallet.py، app/bot/handlers/admin_users.py، app/bot/handlers/admin_orders.py
- Gates/Middlewares: app/bot/middlewares/*
- Logging/Observability: app/logging_config.py، app/utils/correlation.py
- Migrations: app/db/migrations/versions/*
