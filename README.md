# MarzbanSudo

ربات تلگرام برای فروش و مدیریت سرویس‌های Marzban با تکیه بر معماری چندسرویسی، پرداخت از کیف پول و مدیریت سفارش/رسید. این پروژه برای استقرار سریع با Docker آماده شده و از SQLAlchemy Async، httpx، aiogram v3 و Alembic استفاده می‌کند.

## امکانات کلیدی

- ارتباط پایدار با Marzban (token-based + retry/backoff)
- مدل چندسرویسی: هر کاربر می‌تواند چند سرویس داشته باشد (UserService)
- خرید پلن، تمدید سرویس، نمایش لینک اشتراک و QR
- کیف پول کاربر: حداقل/حداکثر شارژ قابل تنظیم، ثبت رسید، تایید/رد توسط ادمین، رد با دلیل
- سفارش‌ها: ثبت رسید، صف تایید ادمین، ثبت رویدادها و لاگ‌ها
- امنیت �� دوام:
  - محدودیت MIME رسیدها (فقط image/* یا application/pdf)
  - Rate-Limit per-user با صف محدود
  - BanGate با مسیر Appeal فقط برای کاربران بن‌شده
- مشاهده‌پذیری (Observability):
  - Correlation-ID middleware و لاگ ساختاریافته JSON با زمینه (user_id, order_id, topup_id, cid)
- زمان‌بند (Worker): sync پلن‌ها از Marzban، اعلان مصرف/انقضا، پاکسازی/اتوکنسل سفارش‌های قدیمی

## معماری و اجزاء

- app/bot/*: هندلرها، میدلورها، کیبوردها
- app/services/*: سرویس‌های دامنه (Marzban، اعلان‌ها، امنیت، زمان‌بند)
- app/marzban/*: کلاینت httpx برای Marzban و اسکیمای مرتبط
- app/db/*: مدل‌ها، نشست پایگاه‌داده و مهاجرت‌ها
- app/utils/*: ابزارهای کمکی (username, money, correlation, intent_store)
- docker-compose.yml + Dockerfile: استقرار سریع با MariaDB و سرویس‌های bot/worker

## پیش‌نیازها

- یک سرور لینوکسی با دسترسی root (یا sudo)
- Docker و Docker Compose v2 (اگر ندارید، اسکریپت خودکار نصب می‌کند)
- دسترسی ادمین به پنل Marzban
- توک�� ربات تلگرام و لیست ادمین‌ها (TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS)

## راه‌اندازی سریع (توصیه‌شده)

### گزینه 1: اسکریپت راه‌اندازی تعاملی (پیشنهادی)

```bash
# حالت تعاملی با UI (اگر whiptail/dialog نصب باشد) و انتخاب Simple/Advanced
bash scripts/setup.sh

# حالت غیرتعاملی برای CI/Automation (از ENV فعلی هم می‌خواند)
TELEGRAM_BOT_TOKEN=XXXX \
TELEGRAM_ADMIN_IDS=111111111,222222222 \
MARZBAN_BASE_URL=https://panel.example.com \
MARZBAN_ADMIN_USERNAME=admin \
MARZBAN_ADMIN_PASSWORD=secret \
APP_ENV=production TZ=Asia/Tehran \
bash scripts/setup.sh --mode simple --non-interactive
```

یادداشت‌ها:
- در حالت Simple/Non-interactive، پسوردهای DB به‌صورت خودکار قوی تولید می‌شوند و DB_URL با URL-encode پسورد ساخته می‌شود.
- در حالت Advanced می‌توانید همه مقادیر را ویرایش کنید؛ اسکریپت ورودی‌ها را اعتبارسنجی می‌کند.
- خروجی نهایی: فایل `.env` کامل در ریشه پروژه.

### گزینه 2: بوت‌استرپ کامل روی سرور خام

اسکریپت بوت‌استرپ جهت استقرار خودکار روی سرور خام:

```bash
# بر روی سرور لینوکسی (به عنوان root یا sudo)
bash scripts/bootstrap.sh

# یا با override متغیرها (مثال):
TELEGRAM_BOT_TOKEN=XXXX \
MARZBAN_BASE_URL=https://your.marzban \
MARZBAN_ADMIN_USERNAME=admin \
MARZBAN_ADMIN_PASSWORD=secret \
TELEGRAM_ADMIN_IDS=111111111,222222222 \
DB_URL="mysql+asyncmy://sudo_user:CHANGE_ME@db:3306/marzban_sudo?charset=utf8mb4" \
DB_PASSWORD=CHANGE_ME DB_ROOT_PASSWORD=CHANGE_ME_ROOT \
bash scripts/bootstrap.sh
```

این اسکریپت:
- در صورت نیاز Docker/Compose را نصب می‌کند
- فایل `.env` را می‌سازد/به‌روزرسانی می‌کند
- دایرکتوری‌های logs و data را ایجاد می‌کند
- سرویس‌ها را با `docker compose up -d --build` بالا می‌آورد
- healthcheck سرویس��ها را بررسی می‌کند و لاگ‌های ربات را نمایش می‌دهد

## راه‌اندازی دستی (جایگزین)

1) فایل `.env` را از روی `.env.example` بسازید و مقادیر کلیدی را تکمیل کنید:

- الزامی:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_ADMIN_IDS`
  - `MARZBAN_BASE_URL`, `MARZBAN_ADMIN_USERNAME`, `MARZBAN_ADMIN_PASSWORD`
  - `DB_URL` (literal password) و `DB_PASSWORD`, `DB_ROOT_PASSWORD` برای کانتینر DB
- توصیه‌شده:
  - `SUB_DOMAIN_PREFERRED`, `LOG_CHAT_ID`, `APP_ENV`, `TZ`
  - `NOTIFY_USAGE_THRESHOLDS`, `NOTIFY_EXPIRY_DAYS`, `RATE_LIMIT_USER_MSG_PER_MIN`

2) سرویس‌ها را اجرا کنید:

```bash
docker compose up -d --build
```

3) لاگ‌ها را ببینید:

```bash
docker logs -f marzban_sudo_bot
```

## دیتابیس و مهاجرت‌ها

- Alembic به `settings.db_url` تکیه می‌کند (env)
- زنجیره مهاجرت‌ها خطی برای استقرار تازه:
  - `20250826_000001_init`
  - `20250829_000002_wallet`
  - `20250830_000003_order_snapshot`
  - `20250902_000003_user_services`
- ربات در بوت، `alembic upgrade head` را اجرا می‌کند (در سرویس bot)

## جریان‌های اصلی ربات

- کاربر:
  - `/start` برای ثبت و نمایش منو
  - مشاهده پلن‌ها، خرید پلن و تمدید سرویس (چندسرویسی)
  - کیف پول: انتخاب مبلغ، ارسال رسید (عکس/PDF)، اطلاع از وض��یت
  - حساب کاربری: نمایش وضعیت، لینک اشتراک، QR، تغییر یوزرنیم با محدودیت دوره‌ای
- ادمین:
  - تایید/رد سفارش‌ها؛ تحویل سرویس به‌صورت service-specific
  - مدیریت کیف پول: تعیین حداقل/حداکثر شارژ، شارژ دستی، رد با دلیل
  - مدیریت پلن‌ها، اعلان‌ها، و سایر تنظیمات از طریق منوهای ادمین

## امنیت و پایداری State

- Receipt فقط image/* یا application/pdf پذیرفته می‌شود
- RateLimiter با صف محدود برای کنترل مصرف حافظه
- BanGate برای کاربران بن‌شده با مسیر Appeal امن
- Stateهای حساس کیف پول (کاربر/ادمین) DB-backed با TTL نرم:
  - `INTENT:TOPUP:{uid}` (amount, ts) با TTL 15 دقیقه
  - `INTENT:WADM:{admin_id}`, `INTENT:WREJ:{admin_id}`, `INTENT:WREJCTX:{admin_id}`

## لاگ‌ها و مشاهده‌پذیری (Observability)

- ساختار لاگ JSON با زمینه:
  - correlation-id (cid)، user_id، order_id، topup_id، admin_id
- فعال‌سازی در production با `LOG_FORMAT=json` (پیش‌فرض production)
- فایل لاگ در `./logs/app.log` (اگر دسترسی نوشتن وجود داشته ب��شد)

## ساختار پوشه‌ها

```
app/
  bot/               # handlers, middlewares, keyboards
  services/          # domain services (marzban, notifications, security, scheduler)
  marzban/           # httpx client wrappers
  db/                # models, session, migrations
  utils/             # helpers (correlation, intent_store, ...)
  main.py            # bot entrypoint
  healthcheck.py     # bot healthcheck
scripts/
  bootstrap.sh       # fresh server bootstrap script
Dockerfile
docker-compose.yml
```

## رفع اشکال (Troubleshooting)

- Bot unhealthy:
  - `docker logs marzban_sudo_bot` را بررسی کنید
  - `TELEGRAM_BOT_TOKEN` و دسترسی شبکه به Marzban را چک کنید
- DB اتصال برقرار نمی‌شود:
  - مطابقت `DB_URL` و `DB_PASSWORD` در `.env` را بررسی کنید
  - سرویس DB باید healthy باشد: `docker inspect marzban_sudo_db`
- Marzban خطا می‌دهد:
  - URL و credentialها و گواهی SSL را بررسی کنید
  - لاگ‌های ارتباط (httpx) با سطح INFO/DEBUG

## توسعه و مشارکت

- Pull Requestها با توضیح مختصر تغییرات و اثرات سیستم پذیرفته می‌شوند
- کامیت‌ها را با Summary/Description کوتاه و استاندارد ارائه دهید

## مجوز

- این پروژه برای استفاده داخلی/سفارشی‌سازی طراحی شده است. در ص��رت نیاز به انتشار عمومی، مجوز مناسب را اضافه کنید.
