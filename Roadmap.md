# MarzbanSudo – Roadmap & Technical Spec (v2)

این سند نقشه راه، مشخصات محصول، معماری، دیتامدل، نگاشت APIهای Marzban 0.8.4، الزامات امنیتی/عملیاتی و اقلام تحویلی را برای توسعه یک ربات تلگرامی فروش/مدیریت اشتراک VPN ارائه می‌کند. سند به‌گونه‌ای نوشته شده که مستقیماً قابل استفاده برای تیم توسعه باشد.

---

## 1) اهداف محصول و دامنه
- بات تلگرام عمومی برای:
  - مشاهده پلن‌ها، خرید اشتراک، شارژ حساب (افزایش حجم)، دریافت لینک‌های Subscription و مشاهده مصرف/انقضا.
  - تجربه کاربری ساده و امن؛ راهنما و لینک‌های مخصوص کلاینت‌ها (v2rayN/v2rayNG/Streisand و JSON).
- کلیه عملیات مدیریتی توسط مالک بات در محیط امن (سرور لینوکس) انجام می‌شود؛ اطلاعات حساس پنل Marzban و سرور صرفاً از طریق «پنل مدیریت لینوکسی» دریافت و نگهداری می‌گردد، نه داخل تلگرام.
- آماده برای فروش/توزیع بات در آینده:
  - طراحی «آماده چند-مستاجری (multi-tenant-ready)» با پروفایل تنظیمات مجزا.
  - لایه پرداخت افزونه‌پذیر (plugin-based) و قابل تعویض بدون تغییر لایه‌های بالاتر.

خارج از دامنه MVP
- درگاه‌های پرداخت آنلاین (فعلاً کارت‌به‌کارت با تایید ادمین).
- پنل وب گرافیکی (در MVP پنل CLI/TUI لینوکسی ارائه می‌شود؛ وب‌پنل در فاز آینده).

---

## 2) الزامات مدیریتی و «پنل مدیریت لینوکسی» (sudoctl)
یک ابزار مدیریتی تعاملی (CLI/TUI) برای سرور لینوکسی ارائه می‌شود که:
- Setup Wizard:
  - دریافت و ذخیره امن تنظیمات/Secrets در .env (خارج از ریپو):
    - MARZBAN_BASE_URL, MARZBAN_ADMIN_USERNAME, MARZBAN_ADMIN_PASSWORD
    - TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS
    - DB_URL, SUB_DOMAIN_PREFERRED, NOTIFY_* و سایر متغیرها
  - تست اتصال به Marzban (POST /api/admin/token) و پایگاه داده.
  - ایجاد/به‌روزرسانی ��ایل‌های env و راه‌اندازی سرویس.
- Control:
  - start/stop/restart/status/logs برای سرویس بات و Worker/Scheduler (روی Docker Compose یا systemd wrapper).
  - rotate secrets (تعویض امن توکن/پسورد) و بازنشانی امن سرویس.
  - backup/restore پایگاه داده و خروجی گرفتن از تنظیمات.
- Profiles (آماده چند-مستاجری):
  - امکان تعریف چند پروفایل مجزا (tenant) با .env و prefix دیتابیس جداگانه.
  - سوییچ سریع بین پروفایل‌ها، یا اجرای چند نمونه هم‌زمان با پورت/نام سرویس متفاوت.
- Diagnostics:
  - healthcheck (DB، Marzban token، reachability)، نوار وضعیت منابع، چاپ نسخه‌ها.
  - اجرای alembic upgrade head قبل از start.
- (آینده) Web Admin Panel سبک روی FastAPI با Basic Auth/IP allowlist (اختیاری).

توزیع/نصب
- Docker Compose به‌عنوان مسیر اصلی اجرا.
- اسکریپت نصب sh برای راه‌اندازی سریع sudoctl، تولید .env‌ها، و تعریف سرویس‌ها.

---

## 3) معماری سیستم
- Bot Service (Telegram): aiogram v3 (async)، هندل منوها/جریان‌ها/ACL ادمین.
- Marzban Client: httpx.AsyncClient با مدیریت Bearer Token، backoff، و re-auth روی 401.
- Database: MariaDB/MySQL با SQLAlchemy 2 (async) + Alembic migrations.
- Scheduler/Worker: کران‌های اعلان مصرف/انقضا، پاکسازی منقضی‌ها، مدیریت سفارش‌ها، sync plans.
- Payment Layer: manual_transfer (MVP)؛ افزونه‌پذیر برای Zarinpal/IDPay در آینده.
- Admin Linux Panel (sudoctl): CLI/TUI روی سرور برای تنظیم/کنترل/پایش.

قواعد کلیدی
- توکن/پسورد فقط روی سرور و در .env نگاه‌داری می‌شود.
- ساخت لینک‌های سابسکریپشن بر اساس token ذخیره‌شده؛ دومین نمایش SUB_DOMAIN_PREFERRED.
- سیاست تمدید: افزودن حجم به data_limit بدون تغییر expire؛ پلن جدید = جایگزینی کامل.
- عملیات idempotent و ایمن در برابر تکرار/خطای شبکه.

---

## 4) پیکربندی و ENV
- متغیرهای کلیدی:
  - APP_ENV=production|staging
  - TZ=Asia/Tehran
  - MARZBAN_BASE_URL, MARZBAN_ADMIN_USERNAME, MARZBAN_ADMIN_PASSWORD
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ADMIN_IDS=comma-separated (مثلاً 111,222)
  - DB_URL=mysql+asyncmy://user:pass@db:3306/marzban_sudo?charset=utf8mb4
  - NOTIFY_USAGE_THRESHOLDS=0.7,0.9
  - NOTIFY_EXPIRY_DAYS=3,1,0
  - SUB_DOMAIN_PREFERRED=irsub.fun
  - LOG_CHAT_ID
  - CLEANUP_EXPIRED_AFTER_DAYS=7
- مدیریت چند-پروفایلی (اختیاری):
  - مسیرها: /opt/marzban-sudo/<profile>/.env ، /opt/marzban-sudo/<profile>/data
  - نام سرویس‌ها با پسوند profile متمایز شوند.

---

## 5) نگاشت فیچرها به API Marzban 0.8.4
- Auth ادمین: POST /api/admin/token → access_token (cache+expiry)
  - روی 401: یک‌بار re-login با قفل سراسری؛ backoff نمایی در خطاهای 5xx/شبکه.
- Templates/Plans: GET /api/user_template و GET /api/user_template/{id} → sync با جدول plans.
- User Lifecycle:
  - ساخت: POST /api/user با username (tg_<telegram_id>)، template_id=1 و override data_limit/expire.
  - دریافت: GET /api/user/{username} → proxies, subscription_url/token, expire, data_limit, usage base.
  - تمدید (افزایش حجم): PUT /api/user/{username} با data_limit جدید (جمع فعلی + خرید).
  - جایگزینی کامل: PUT data_limit و expire جدید + POST /reset → (اختیاری) /revoke_sub.
  - لینک‌ها/مصرف برای کاربر: /sub4me/{token}/, /info, /usage, /{client_type}.
- منقضی‌ها: GET /api/users/expired و DELETE /api/users/expired برای پاکسازی دوره‌ای.

نکات پیاده‌سازی Client
- timeoutها: connect/read/write=5–10s، total=15–30s.
- retries: روی 429/502/503/504 با backoff و jitter؛ سقف تلاش و circuit breaker سبک.
- validation: ورودی/خروجی با pydantic (schemas.py).

---

## 6) دیتامدل (ORM)
- users
  - id PK, tenant_id (nullable برای تک‌مستاجری), telegram_id UNIQUE, marzban_username UNIQUE
  - subscription_token, status ENUM(active|disabled|expired|deleted)
  - expire_at TIMESTAMP(UTC), data_limit_bytes BIGINT UNSIGNED, last_usage_bytes BIGINT, last_usage_ratio FLOAT
  - last_notified_usage_threshold FLOAT, last_notified_expiry_day INT
  - created_at, updated_at
- plans
  - id PK, tenant_id, template_id UNIQUE, title, price DECIMAL(12,2), currency
  - duration_days INT, data_limit_bytes BIGINT, description TEXT, is_active BOOL, updated_at
- orders
  - id PK, tenant_id, user_id FK, plan_id FK
  - status ENUM(pending|paid|provisioned|failed|cancelled)
  - amount DECIMAL(12,2), currency, provider ENUM(manual_transfer|zarinpal|idpay|...)
  - provider_ref VARCHAR(191), receipt_file_path TEXT, admin_note TEXT
  - idempotency_key VARCHAR(191) UNIQUE, created_at, updated_at, paid_at, provisioned_at
- transactions (برای درگاه‌ها)
  - id PK, tenant_id, order_id FK UNIQUE, status, payload_raw JSON, signature_valid BOOL, created_at
- audit_logs
  - id PK, tenant_id, actor(admin|user|system), action, target_type, target_id, meta JSON, created_at

Indexها و قیود
- users(telegram_id), users(marzban_username), users(expire_at), users(status)
- orders(user_id,status,created_at), orders(idempotency_key)
- plans(template_id,is_active)

همزمانی/قفل‌گذاری
- در مسیر Provision از قفل ردیفی (SELECT ... FOR UPDATE) یا قفل اپلیکیشنی بر اساس (order_id یا user_id) استفاده شود.
- Idempotency: تکرار عملیات Provision با idempotency_key بی‌اثر گردد.

---

## 7) جریان‌های عملیاتی
- نام‌گذاری کا��بر: tg_<telegram_id>
- خرید اولیه
  1) ایجاد Order(pending) با مبلغ/پلن انتخابی
  2) کاربر آپلود رسید/اطلاعات کارت‌به‌کارت → صف بررسی ادمین
  3) تایید ادمین → Provision:
     - اگر کاربر وجود ندارد: POST /api/user با data_limit/expire از plan
     - اگر وجود دارد و سیاست «خرید جدید=جایگزینی کامل»: PUT data_limit/expire جدید + POST reset + (اختیاری) revoke_sub
  4) خواندن GET user و ذخیره subscription_token → ارسال لینک‌ها به کاربر
- شارژ (تمدید/افزایش حجم)
  - GET user → new_limit = current.data_limit + plan.data_limit_bytes
  - PUT user با data_limit=new_limit (expire بدون تغییر)
  - تایید state با GET user و به‌روزرسانی DB
- مدیریت منقضی‌ها
  - اعلان تمدید به کاربر در 3/1/0 روز مانده
  - تغییر status به expired/disabled پس از تاریخ
  - پاکسازی خودکار بعد از CLEANUP_EXPIRED_AFTER_DAYS (soft-delete داخلی؛ حذف Marzban در صورت سیاست)

خطا و Retry
- روی خطاهای موقتی شبکه/Marzban از backoff+jitter استفاده شود.
- هر Provision idempotent و قابل تکرار بدون اثر جانبی.

---

## 8) Bot (aiogram v3)
- ساختار
  - routers: start, plans, orders, account, admin
  - middlewares: auth/admin ACL، rate-limit per-user، logging/correlation-id
  - keyboards: inline با صفحات‌بندی؛ تایید/رد سفارش؛ بازگشت
  - filters: فقط ادمین، وضعیت کاربر
- فلو کاربر
  - /start → نمایش پلن‌ها → انتخاب پلن → Order(pending) + نمایش مبلغ/کارت مقصد + راهنمای ارسال رسید
  - پس از تایید ادمین → ارسال subscription_url و لینک‌های client_type + راهنمای نصب
  - اکانت من: وضعیت، مصرف (sub4me/usage)، انقضا، لینک‌ها (بدون Reset)
- فلو ادمین
  - صف سفارش‌ها با inline approve/reject و مشاهده رسید
  - جستجو tg_<telegram_id> یا username
  - revoke_sub، گزارش خطا به LOG_CHAT_ID
- UX/متن‌ها
  - پیام‌ها کوتاه/روشن؛ مقایسه «تمدید (افزایش حجم)» در برابر «خرید پلن جدید (جایگزینی کامل)»
  - ساخت لینک‌ها بر اساس SUB_DOMAIN_PREFERRED و token ذخیره‌شده

---

## 9) Scheduler/Worker
- اعلان مصرف: هر 1 ساعت
  - sub4me/usage → تشخیص عبور از آستانه‌های 70%/90%
  - ارسال پیام یک‌بار برای هر آستانه (با last_notified_usage_threshold)
- اعلان انقضا: روزانه ساعت 10 محلی
  - روزهای 3/1/0 مانده → دی‌دیوپلیکیشن با last_notified_expiry_day
- سفارش‌ها
  - pending بیش از N ساعت → auto-cancel + اعلان
- Sync Templates/Plans
  - هر 6 ساعت از Marzban → به‌روزرسانی plans (اجازه override عنوان/قیمت در DB)
- پاکسازی منقضی‌ها و گزارش وضعیت به LOG_CHAT_ID

---

## 10) امنیت و انطباق
- جدا‌سازی نقش‌ها: ادمین Marzban اختصاصی برای بات با حداقل دسترسی.
- Secrets فقط در .env سرور؛ امکان rotate از sudoctl.
- Rate-limit درخواست‌ها و پیام‌ها؛ ورودی‌ها sanitize/validate.
- لاگ‌برداری ساخت‌یافته بدون اطلاعات حساس؛ ارسال خطاها به LOG_CHAT_ID.
- محدودسازی شبکه کانتینر بات به آدرس‌های لازم (Marzban/پرداخت).
- زمان‌ها UTC؛ TZ کانتینر تنظیم؛ تبدیل نمایش برای کاربر.
- TLS verification فعال؛ گزینه pinning CA در تولید.
- نگهداری مدارک/رسیدها با retention تعریف��شده و حذف دوره‌ای.

---

## 11) پرداخت (MVP: کارت‌به‌کارت) و افزونه‌ها
- MVP manual_transfer
  - ایجاد Order(pending) با مبلغ/کارت مقصد (نام بانک، چهار رقم آخر، صاحب کارت)
  - آپلود رسید/متن تراکنش توسط کاربر → صف تایید ادمین → Provision
  - idempotency با قفل روی order_id/idempotency_key
- Interface افزونه پرداخت (آینده)
  - providers/{provider}.py با توابع: create_invoice, verify_callback, capture, refund
  - transactions برای ذخیره payload/signature و audit.

---

## 12) دیپلوی، عملیات و مانیتورینگ
- Docker Compose
  - services: bot, db (MariaDB 10.11) [+ worker اختیاری]
  - healthchecks، restart policy، resource limits، log rotation
  - env_file: .env های پروفایل از sudoctl
- Migrations: alembic upgrade head در startup (توسط sudoctl)
- Backup: dump شبانه DB + retention 7/30 روز
- Observability
  - structured logs JSON، سطح INFO/ERROR
  - correlation-id per update/message
  - هشدار خطاهای 4xx/5xx Marzban و استثناها به LOG_CHAT_ID

---

## 13) تست و پذیرش
- واحد (Unit)
  - Marzban client (mock httpx): token refresh، retry/backoff، map خطاها
  - محاسبه expire/limit، تولید لینک‌ها، parser پیام‌ها
- یکپارچه (Integration)
  - اتصال به Marzban dev/staging، سناریوهای Provision/Retry/Timeout/429
  - مسیر manual_transfer و تایید ادمین end-to-end
- پذیرش (Acceptance)
  - کاربر: خرید اولیه و دریافت subscription_url و لینک‌های v2ray/v2ray-json
  - تمدید با افزودن حجم بدون تغییر expire و نمایش صحیح sub4me/info
  - پرداخت دستی با تایید ادمین و Provision idempotent
  - اعلان‌های مصرف/انقضا؛ لاگ رخدادها برای ادمین
  - پنل لینوکسی: setup، start/stop/status/logs، rotate secrets، backup/restore

---

## 14) فازبندی اجرا و اقلام تحویلی
- فاز 0 – زیرساخت و نصب
  - docker-compose, MariaDB, .env نمونه، اسکریپت نصب sudoctl
  - healthcheck و اتصال موفق به /api/admin/token
  - اقلام: docker-compose.yml, requirements.txt, alembic init, sudoctl (CLI اولیه)
- فاز 1 – Marzban Client و Auth
  - httpx client با token cache/refresh، schemas pydantic، تست‌های واحد
  - اقلام: app/marzban/client.py, schemas.py, tests
- فاز 2 – ORM و CRUD + Sync Plans
  - جداول users/plans/orders/transactions/audit_logs و CRUD
  - job sync user_template → plans (override عنوان/قیمت)
  - اقلام: app/db/models.py, crud/*, migrations/*
- فاز 3 – Bot Skeleton
  - routers: start/plans/orders/account/admin، keyboards/middlewares/filters
  - پیام‌های اولیه و صفحات پلن‌ها/سفارش‌ها
  - اقلام: app/bot/*, logging_config.py
- فاز 4 – پرداخت دستی و Provision
  - آپلود رسید، صف تایید ادمین، قفل idempotent، Provision end-to-end
  - ارسال لینک‌های client_type و راهنما
  - اقلام: app/payment/manual_transfer.py, services/provisioning.py, services/billing.py
- فاز 5 – Scheduler و مدیریت منقضی‌ها
  - اعلان مصرف/انقضا، cleanup منقضی‌ها، مدیریت سفارش‌های معوق
  - اقلام: services/notifications.py, services/scheduler.py
- فاز 6 – ام��یت/لاگ/مانیتورینگ
  - rate-limit، سخت‌سازی دسترسی‌ها، گزارش خطاها به LOG_CHAT_ID، backup
  - اقلام: services/security.py, بهبود لاگ‌ها، اسناد عملیاتی
- فاز 7 – نهایی‌سازی و آماده‌سازی فروش/توزیع
  - مستندسازی نصب/راه‌اندازی، بهبود sudoctl (profiles، rotate)، بسته نصب
  - اقلام: docs، اسکریپت‌های نصب/به‌روزرسانی، چک‌لیست انتشار

---

## 15) معیارهای پذیرش (DoD)
- کاربر نهایی
  - دیدن پلن‌ها، ایجاد سفارش، آپلود رسید، دریافت subscription_url + لینک‌های v2ray/v2ray-json
  - تمدید با افزودن حجم بدون تغییر expire؛ مشاهده مصرف/انقضا از sub4me/info
- ادمین
  - تایید/رد سفارش‌ها در بات؛ revoke_sub در صورت نیاز
  - گزارش رخداد/خطا به LOG_CHAT_ID
- عملیات
  - راه‌اندازی با sudoctl: setup, start/stop/status/logs, rotate secrets, backup/restore
  - jobs اعلان مصرف/انقضا و cleanup منقضی‌ها
  - idempotency در Provision و مقاوم بودن در برابر retry/قطع

---

## 16) نکات اجرایی مهم
- template_id اولیه = 1 با data_limit/expire صفر؛ حین ساخت یوزر باید override شود.
- active-next فعلاً استفاده نمی‌شود.
- Reset مصرف برای کاربر مجاز نیست؛ فقط در سناریوی جایگزینی کامل توسط ادمین.
- ذخیره فقط subscription_token در DB؛ URLها در لحظه نمایش با SUB_DOMAIN_PREFERRED ساخته شوند.
- واحدها: data_limit برحسب بایت (BIGINT)؛ Helper تبدیل GB/MB برای نمایش.
- زمان‌ها UTC؛ نمایش محلی؛ TZ کانتینر تنظیم.
- domain rewriting صرفاً در لایه نمایش؛ state در Marzban منبع حقیقت است.
- نگهداری رسیدها با مدت نگهداری مشخص و حذف دوره‌ای.

---

## 17) الحاقیه – مثال‌های API
- ساخت کاربر جدید (template_id=1، override حجم/انقضا)

POST /api/user HTTP/1.1 (Authorization: Bearer <token>)
{
  "username": "tg_262182607",
  "template_id": 1,
  "data_limit": 53687091200,
  "expire": 1759301999,
  "note": "plan: 50GB/30d"
}

- افزودن حجم (تمدید)

PUT /api/user/tg_262182607 HTTP/1.1 (Authorization: Bearer <token>)
{ "data_limit": <new_limit_bytes> }

- لینک‌های ساب (با token)
  - عمومی: https://irsub.fun/sub4me/{token}/
  - v2ray: https://irsub.fun/sub4me/{token}/v2ray
  - JSON:  https://irsub.fun/sub4me/{token}/v2ray-json
