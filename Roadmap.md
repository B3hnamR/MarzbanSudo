# MarzbanSudo – Roadmap & Technical Spec (v3)

این سند نقشه راه، پیش‌نیازها، دستورالعمل نصب و راه‌اندازی، مشخصات معماری، دیتامدل، نگاشت APIهای Marzban 0.8.4، الزامات امنیتی/عملیاتی و اقلام تحویلی را برای توسعه و استقرار یک ربات تلگرامی فروش/مدیریت اشتراک VPN ارائه می‌کند. نسخه v3 شامل تمامی موارد لازم برای «راه‌اندازی بدون ابهام» است و قابل تحویل مستقیم به تیم توسعه/عملیات می‌باشد.

---

## 0) TL;DR – چک‌لیست راه‌اندازی سریع
1) آماده‌سازی سرور لینوکسی (Ubuntu 22.04/24.04)، به‌روزرسانی، تنظیم TZ و NTP، نصب Docker/Compose، UFW.
2) آماده‌سازی Marzban 0.8.4 (API فعال، ادمین اختصاصی بات، وجود template_id=1 با data_limit/expire=0).
3) ساخت بات در BotFather، فعال‌سازی Privacy Mode و تنظیم دستورات؛ دریافت TELEGRAM_BOT_TOKEN.
4) راه‌اندازی MariaDB/MySQL (ایجاد DB/User utf8mb4)، فعال‌سازی پشتیبان‌گیری و تست بازیابی.
5) کلون ریپو، ساخت پروفایل /opt/marzban-sudo/<profile> و تولید .env کامل (Secrets فقط روی سرور).
6) اجرای مهاجرت‌ها (alembic upgrade head) و start سرویس‌ها (bot [+worker]).
7) تست اتصال (healthcheck)، sync templates→plans، تست سناریوی خرید اولیه و تمدید.
8) فعال‌سازی Scheduler اعلان مصرف/انقضا، backup Cron و log rotation؛ چک‌لیست Go-Live.

---

## 1) اهداف محصول و دامنه
- بات تلگرام عمومی برای:
  - مشاهده پلن‌ها، خرید اشتراک، شارژ حساب (افزایش حجم)، دریافت لینک‌های Subscription و مشاهده مصرف/انقضا.
  - تجربه کاربری ساده و امن با لینک‌های مخصوص کلاینت‌ها (v2rayN/v2rayNG/Streisand و JSON).
- عملیات مدیریتی و Secrets فقط از طریق «پنل مدیریت لینوکسی (sudoctl)» روی سرور انجام می‌شود، نه داخل تلگرام.
- آمادگی فروش/چند-مستاجری (multi-tenant-ready) با پروفایل‌های مستقل و قابل اجرای هم‌زمان.

خارج از دامنه MVP
- درگاه‌های پرداخت آنلاین (MVP کارت‌به‌کارت).
- پنل وب گرافیکی (فعلاً CLI/TUI لینوکسی؛ وب‌پنل در فاز بعد).

---

## 2) معماری سیستم
- Bot Service (Telegram): aiogram v3 (async) برای منو/جریان‌ها/ACL ادمین؛ حالت اجرا: Polling (Webhook اختیاری در آینده با Nginx/Certbot).
- Marzban Client: httpx.AsyncClient با مدیریت Bearer Token، backoff+jitter، re-auth روی 401 (با قفل).
- Database: MariaDB/MySQL با SQLAlchemy 2 (async) + Alembic migrations.
- Scheduler/Worker: اعلان مصرف/انقضا، مدیریت سفارش‌ها، sync plans، cleanup منقضی‌ها.
- Payment: manual_transfer (MVP)؛ افزونه‌پذیر برای Zarinpal/IDPay.
- Admin Linux Panel (sudoctl): CLI/TUI برای setup، کنترل سرویس‌ها، rotate، backup/restore، پروفایل‌ها.

قواعد کلیدی
- Secrets فقط در .env سرور نگهداری می‌شوند و قابل rotate از sudoctl هستند.
- ساخت لینک‌های subscription از روی token ذخیره‌شده �� SUB_DOMAIN_PREFERRED برای نمایش.
- تمدید = افزودن حجم؛ خرید پلن جدید = جایگزینی کامل (reset + اختیاری revoke_sub).
- عملیات idempotent، قفل‌گذاری مناسب و مقاوم به retry/قطعی شبکه.

---

## 3) پیش‌نیازهای سیستم و شبکه
- سیستم‌عامل: Ubuntu Server 22.04 LTS یا 24.04 LTS.
- منابع حداقلی: 1–2 vCPU، 2–4 GB RAM، 20+ GB SSD، شبکه پایدار.
- زمان/منطقه: TZ=Asia/Tehran، NTP فعال (chrony/systemd-timesyncd)، تمام زمان‌ها در DB/سرویس UTC.
- بسته‌ها: ca-certificates، curl، git، ufw، unzip، jq.
- فایروال (UFW):
  - ورودی: SSH (22/tcp) فقط از IP ادمین؛ سایر ورودی‌ها بسته مگر نیاز خاص.
  - خروجی: اجازه 443/tcp به MARZBAN_BASE_URL و درگاه‌های پرداخت (آینده).
- DNS/TLS:
  - MARZBAN_BASE_URL باید HTTPS معتبر داشته باشد و از سرور قابل دسترس باشد.
  - SUB_DOMAIN_PREFERRED (مثلاً irsub.fun) فقط برای نمایش لینک‌ها استفاده می‌شود؛ نیاز به تغییر DNS نیست مگر قصد فوروارد داشته باشید.
- کاربران/دسترسی:
  - SSH Key-Only، غیرفعال‌سازی PasswordAuth، کاربر غیر روت برای اجرا.

نمونه تنظیمات سریع
```bash
sudo timedatectl set-timezone Asia/Tehran
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl git ufw unzip jq
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <YOUR_IP> to any port 22 proto tcp
sudo ufw enable
```

---

## 4) آماده‌سازی Marzban
- نسخه پنل: Marzban 0.8.4، API فعال.
- ادمین اختصاصی بات: کاربر مجزا با پسورد قوی؛ حداقل سطح دسترسی.
- Template اولیه: template_id=1 با data_limit=0 و expire=0 (override در ساخت).
- تست اتصال API:
```http
POST {MARZBAN_BASE_URL}/api/admin/token
{ "username": "<admin>", "password": "<pass>" }
```
- چک‌لیست: HTTPS معتبر، دسترسی از سرور، تست /api/user_template و /api/user.

---

## 5) ساخت Bot در BotFather
- ساخت بات و دریافت TELEGRAM_BOT_TOKEN.
- تنظیم Privacy Mode → ON (برای گروه‌ها؛ مکالمه مستقیم مشکلی ندارد).
- تعریف دستورات پیشنهادی:
```
start - شروع و مشاهده منو
plans - مشاهده پلن‌ها
orders - سفارش‌های من
account - وضعیت اکانت/لینک‌ها
admin - پنل ادمین (فقط مدیران)
```
- دریافت TELEGRAM_ADMIN_IDS (شناسه‌های عددی مدیران) و فعال‌سازی 2FA روی حساب تلگرام ادمین‌ها.

---

## 6) پایگاه داده (MariaDB/MySQL)
- نصب MariaDB 10.11 LTS (یا MySQL 8)، bind-address فقط داخلی.
- ایجاد DB/User با utf8mb4.
```sql
CREATE DATABASE marzban_sudo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sudo_user'@'%' IDENTIFIED BY 'STRONG_PASS_HERE';
GRANT ALL PRIVILEGES ON marzban_sudo.* TO 'sudo_user'@'%';
FLUSH PRIVILEGES;
```
- توصیه تنظیمات: innodb_flush_log_at_trx_commit=1، sync_binlog=1، time_zone='+00:00'.
- پشتیبان‌گیری: mysqldump شبانه + تست بازیابی ماهانه.

---

## 7) نصب Docker Engine و Compose
- نصب Docker و compose-plugin:
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# relogin
sudo apt -y install docker-compose-plugin
sudo systemctl enable --now docker
```
- محدودیت منابع و log rotation:
```bash
sudo mkdir -p /etc/docker
cat | sudo tee /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": {"max-size": "50m", "max-file": "3"}
}
JSON
sudo systemctl restart docker
```

---

## 8) ساختار پروژه و پروفایل‌ه�� (multi-tenant-ready)
- مسیر پایه: /opt/marzban-sudo/<profile>
```
/opt/marzban-sudo/
  prod/
    .env
    data/
    backups/
  staging/
    .env
    data/
```
- نام‌گذاری سرویس‌ها با پسوند profile برای اجرای هم‌زمان.

---

## 9) پیکربندی ENV و قالب .env
- متغیرهای کلیدی:
  - APP_ENV=production|staging
  - TZ=Asia/Tehran
  - MARZBAN_BASE_URL, MARZBAN_ADMIN_USERNAME, MARZBAN_ADMIN_PASSWORD
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ADMIN_IDS=111111111,222222222
  - DB_URL=mysql+asyncmy://sudo_user:STRONG_PASS_HERE@db:3306/marzban_sudo?charset=utf8mb4
  - NOTIFY_USAGE_THRESHOLDS=0.7,0.9
  - NOTIFY_EXPIRY_DAYS=3,1,0
  - SUB_DOMAIN_PREFERRED=irsub.fun
  - LOG_CHAT_ID
  - CLEANUP_EXPIRED_AFTER_DAYS=7
  - PENDING_ORDER_AUTOCANCEL_HOURS=12
  - RATE_LIMIT_USER_MSG_PER_MIN=20
  - RECEIPT_RETENTION_DAYS=30

نمونه .env (قالب)
```env
APP_ENV=production
TZ=Asia/Tehran
MARZBAN_BASE_URL=https://p.v2pro.store
MARZBAN_ADMIN_USERNAME=botadmin
MARZBAN_ADMIN_PASSWORD=CHANGE_ME
TELEGRAM_BOT_TOKEN=CHANGE_ME
TELEGRAM_ADMIN_IDS=111111111,222222222
DB_URL=mysql+asyncmy://sudo_user:CHANGE_ME@db:3306/marzban_sudo?charset=utf8mb4
SUB_DOMAIN_PREFERRED=irsub.fun
NOTIFY_USAGE_THRESHOLDS=0.7,0.9
NOTIFY_EXPIRY_DAYS=3,1,0
CLEANUP_EXPIRED_AFTER_DAYS=7
PENDING_ORDER_AUTOCANCEL_HOURS=12
RATE_LIMIT_USER_MSG_PER_MIN=20
RECEIPT_RETENTION_DAYS=30
LOG_CHAT_ID=CHANGE_ME
```
- سطح دسترسی فایل .env: 600 و مالک کاربر سرویس.

---

## 10) نگاشت فیچرها به API Marzban 0.8.4
- Auth ادمین: POST /api/admin/token → access_token (cache+expiry)
  - روی 401: یک‌بار re-login با قفل سراسری؛ backoff نمایی روی 5xx/429.
- Templates/Plans: GET /api/user_template و GET /api/user_template/{id} → sync با جدول plans.
- User Lifecycle:
  - ساخت: POST /api/user با username (tg_<telegram_id>)، template_id=1 و override data_limit/expire.
  - دریافت: GET /api/user/{username} → proxies, subscription_url/token, expire, data_limit, usage base.
  - تمدید: PUT /api/user/{username} با data_limit جدید (جمع فعلی + خرید).
  - جایگزینی کامل: PUT data_limit و expire جدید + POST /reset → (اختیاری) /revoke_sub.
  - لینک‌ها/مصرف: /sub4me/{token}/, /info, /usage, /{client_type}.
- منقضی‌ها: GET /api/users/expired و DELETE /api/users/expired.

نکات Client
- timeoutها: connect/read/write=5–10s، total=15–30s؛ retries با backoff+jitter؛ circuit breaker سبک.
- validation با pydantic؛ mapping خطاها و پیام‌های مناسب.

---

## 11) دیتامدل (ORM)
- users: id, tenant_id, telegram_id UNIQUE, marzban_username UNIQUE, subscription_token, status(enum: active|disabled|expired|deleted), expire_at UTC, data_limit_bytes BIGINT, last_usage_bytes, last_usage_ratio, last_notified_usage_threshold, last_notified_expiry_day, created_at, updated_at
- plans: id, tenant_id, template_id UNIQUE, title, price DECIMAL(12,2), currency, duration_days, data_limit_bytes, description, is_active, updated_at
- orders: id, tenant_id, user_id FK, plan_id FK, status(enum: pending|paid|provisioned|failed|cancelled), amount DECIMAL(12,2), currency, provider(enum: manual_transfer|...), provider_ref, receipt_file_path, admin_note, idempotency_key UNIQUE, created_at, updated_at, paid_at, provisioned_at
- transactions: id, tenant_id, order_id FK UNIQUE, status, payload_raw JSON, signature_valid, created_at
- audit_logs: id, tenant_id, actor, action, target_type, target_id, meta JSON, created_at

Indexها: users(telegram_id), users(marzban_username), users(expire_at), users(status), orders(user_id,status,created_at), orders(idempotency_key), plans(template_id,is_active)

قفل‌گذاری و Idempotency: قفل ردیفی یا اپلیکیشنی بر اساس user_id/order_id؛ تکرار Provision بی‌اثر شود.

---

## 12) جریان‌های عملیاتی
- نام‌گذاری: tg_<telegram_id>
- خرید اولیه: Order(pending) → آپلود رسید → تایید ادمین → Provision (ساخت یا جایگزینی کامل) → ارسال subscription_url/لینک‌ها
- شارژ (تمدید/افزایش حجم): GET user → new_limit = current + plan.limit → PUT user → تایید state → به‌روزرسانی DB
- مدیریت منقضی‌ها: اعلان تمدید 3/1/0 روز؛ تغییر status به expired/disabled؛ cleanup بعد از CLEANUP_EXPIRED_AFTER_DAYS

خطا/Retry: backoff+jitter روی 429/5xx؛ هر Provision idempotent.

Edge Cases
- کاربر در Marzban وجود دارد ولی در DB داخلی نیست: در اولین استعلام GET user، رکورد کاربر با telegram_id ملحق یا با ابزار ادمین resolve شود.
- حذف کاربر در Marzban ولی وجود در DB: در نمایش/Provision مدیریت recreate یا soft-delete داخلی.

---

## 13) Bot (aiogram v3)
- routers: start, plans, orders, account, admin
- middlewares: auth/admin ACL، rate-limit per-user، logging/correlation-id
- keyboards: inline با صفحات‌بندی؛ تایید/رد سفارش؛ بازگشت
- filters: فقط ادمین، وضعیت کاربر
- UX/متن‌ها: شفاف‌سازی تفاوت «تمدید (افزایش حجم)» و «پلن جدید (جایگزینی کامل)»؛ لینک‌ها ب�� اساس SUB_DOMAIN_PREFERRED

ورودی‌های سفارش (manual_transfer)
- مبلغ (auto از plan)، متن تراکنش (شماره پیگیری/کارت)، اسکرین‌شات اختیاری.
- صف ادمین: مشاهده رسید/اطلاعات، Approve/Reject با توضیح.

---

## 14) Scheduler/Worker
- اعلان مصرف: هر 1 ساعت (آستانه‌های 70%/90%) با last_notified_usage_threshold
- اعلان انقضا: روزانه ساعت 10 محلی با last_notified_expiry_day
- سفارش‌ها: auto-cancel سفارش‌های pending پس از PENDING_ORDER_AUTOCANCEL_HOURS
- Sync Templates/Plans: هر 6 ساعت
- Cleanup منقضی‌ها و گزارش وضعیت به LOG_CHAT_ID

تنظیمات منابع
- Pool دیتابیس: 10–20 کانکشن async.
- محدودکننده نرخ پیام: RATE_LIMIT_USER_MSG_PER_MIN.

---

## 15) امنیت و سخت‌سازی
- حداقل دسترسی ادمین Marzban؛ تغییر دوره‌ای پسورد/توکن از sudoctl
- Secrets فقط در .env سرور (chmod 600)؛ بدون commit به ریپو
- کانتینر non-root، محدودیت منابع، شبکه محدود شده (فقط outbound لازم)
- TLS verification روشن و امکان CA pinning
- UFW سخت‌گیرانه؛ Fail2ban روی SSH (اختیاری)
- حذف اطلاعات حساس از لاگ‌ها؛ masking توکن‌ها؛ سطح لاگ production = INFO
- سیاست نگهداری رسیدها: RECEIPT_RETENTION_DAYS و حذف دوره‌ای
- GDPR/PII: ذخیره حداقلی داده‌ها، امکان purge کاربر در صورت درخواست

---

## 16) پرداخت (MVP: کارت‌به‌کارت) و افزونه‌ها
- manual_transfer: مبلغ، کارت مقصد (نام بانک، چهار رقم آخر، صاحب کارت)، آپلود رسید، تایید ادمین، Provision idempotent
- Interface آینده: providers/{provider}.py با create_invoice, verify_callback, capture, refund و جدول transactions

---

## 17) دیپلوی، عملیات و مانیتورینگ
- Docker Compose: services (bot, db [+worker])، healthchecks، restart policy، resource limits، log rotation
- مهاجرت‌ها: alembic upgrade head در startup (یا توسط sudoctl قبل از start)
- Backup: dump شبانه + retention 7/30 روز + تست بازیابی ماهانه
- Observability: structured logs JSON، correlation-id per update، هشدار خطاها به LOG_CHAT_ID
- Optional: Sentry/OTel/Prometheus در فاز بعدی

نمونه Healthcheck دستی
```bash
# DB
mysql -h <dbhost> -u sudo_user -p -e 'SELECT 1;'
# Marzban token
curl -s -X POST "$MARZBAN_BASE_URL/api/admin/token" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$MARZBAN_ADMIN_USERNAME\",\"password\":\"$MARZBAN_ADMIN_PASSWORD\"}" | jq .
```

---

## 18) Runbook استقرار و Rollback
1) آماده‌سازی سرور و UFW طبق بخش 3
2) نصب Docker/Compose طبق بخش 7
3) آماده‌سازی DB طبق بخش 6
4) آماده‌سازی Marzban طبق بخش 4
5) ساخت Bot در BotFather طبق بخش 5
6) کلون ریپو و ساخت پروفایل
```bash
sudo mkdir -p /opt/marzban-sudo/prod/{data,backups}
cd /opt/marzban-sudo/prod
cp /path/to/repo/.env.example .env  # یا ساخت .env طبق قالب بخش 9
chmod 600 .env
```
7) اجرای مهاجرت‌ها و راه‌اندازی سرویس‌ها
```bash
# با sudoctl (وقتی آماده شد):
sudoctl setup --profile prod
sudoctl migrate --profile prod
sudoctl start --profile prod

# یا موقتاً با compose:
docker compose up -d db
# انتظار برای آماده شدن DB
# اجرای alembic upgrade head (داخل کانتینر bot یا یک کانتینر ابزار)
docker compose up -d bot  # شامل اجرای ربات پس از مهاجرت
```
8) اعتبارسنجی و Sync
- تست health، بررسی لاگ‌ها، اجرای job sync templates→plans
9) تست سناریوهای کاربر (خرید اولیه، تمدید)
10) فعال‌سازی Scheduler، backup cron و log rotation

Rollback (بازگشت)
- توقف سرویس، بازیابی آخرین backup DB، بازگردانی .env قبلی، start مجدد.

---

## 19) چک‌لیست Go-Live
- [ ] تست موفق token Marzban و GET user_template
- [ ] ایجاد حداقل یک plan فعال پس از sync
- [ ] ارسال پیام‌های اعلان به LOG_CHAT_ID کار می‌کند
- [ ] سفارش دستی، تایید ادمین، Provision، دریافت لینک‌ها موفق
- [ ] تمدید با افزایش حجم و عدم تغییر expire تایید شد
- [ ] اعلان مصرف 70%/90% و انقضا 3/1/0 روز تست شد
- [ ] backup شبانه و log rotation فعال
- [ ] UFW/SSH سخت‌سازی، فایل .env با مجوز 600

---

## 20) تست و پذیرش
- واحد (Unit): Marzban client (token refresh، retry/backoff، map خطاها)، محاسبه expire/limit، تولید لینک‌ها
- یکپارچه (Integration): Marzban dev/staging، خطاهای موقتی/Timeout/429، manual_transfer end-to-end
- پذیرش (DoD):
  - کاربر: خرید اولیه، دریافت subscription_url و لینک‌های v2ray/v2ray-json
  - تمدید با افزایش حجم بدون تغییر expire، sub4me/info صحیح
  - پرداخت دستی با تایید ادمین و Provision idempotent
  - اعلان‌های مصرف/انقضا و گزارش رخدادها به LOG_CHAT_ID
  - sudoctl: setup، start/stop/status/logs، rotate secrets، backup/restore

---

## 21) فازبندی اجرا و اقلام تحویلی
- فاز 0 – زیرساخت
  - docker-compose, MariaDB, .env نمونه، اسکریپت نصب sudoctl
  - اتصال موفق به /api/admin/token
  - اقلام: docker-compose.yml, requirements.txt, alembic init, sudoctl (CLI اولیه)
- فاز 1 – Marzban Client و Auth
  - httpx client با token cache/refresh، schemas pydantic، تست‌های واحد
  - اقلام: app/marzban/client.py, schemas.py, tests
- فاز 2 – ORM و CRUD + Sync Plans
  - جداول users/plans/orders/transactions/audit_logs و CRUD
  - job sync user_template → plans
  - اقلام: app/db/models.py, crud/*, migrations/*
- فاز 3 – Bot Skeleton
  - routers: start/plans/orders/account/admin، keyboards/middlewares/filters
  - اقلام: app/bot/*, logging_config.py
- فاز 4 – پرداخت دستی و Provision
  - آپلود رسید، صف تایید ادمین، قفل idempotent، لینک‌ها
  - اقلام: app/payment/manual_transfer.py, services/provisioning.py, services/billing.py
- فاز 5 – Scheduler و Expireds
  - اعلان‌ها، cleanup، سفارش‌های معوق
  - اقلام: services/notifications.py, services/scheduler.py
- فاز 6 – امنیت/لاگ/مانیتورینگ
  - rate-limit، rotate، backup، اسناد عملیاتی
  - اقلام: services/security.py, scripts/*
- فاز 7 – انتشار و فروش/چند-مستاجری
  - مستندسازی نصب/راه‌اندازی، بهبود sudoctl (profiles)، بسته نصب
  - اقلام: docs، اسکریپت‌های نصب/به‌روزرسانی، چک‌لیست انتشار

---

## 22) نکات اجرایی مهم
- template_id=1 با data_limit/expire صفر؛ در ساخت یوزر override شود
- active-next فعلاً استفاده نمی‌شود
- Reset مصرف برای کاربر ممنوع؛ فقط در جایگزینی کامل (ادمین)
- فقط token را ذخیره کنید؛ URLها هنگام نمایش با SUB_DOMAIN_PREFERRED ساخته شوند
- واحدها بر حسب بایت (BIGINT)، Helper تبدیل GB/MB
- زمان‌ها UTC؛ نمایش محلی؛ TZ کانتینر تنظیم
- domain rewriting صرفاً در لایه نمایش؛ Marzban منبع حقیقت

---

## 23) الحاقیه – مثال‌های API
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
