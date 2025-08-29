# MarzbanSudo – Handover & Operations Guide (v1)

این سند برای واگذاری پروژه به توسعه‌دهنده/اپراتور جدید تهیه شده است. شامل معرفی کلی، نحوه راه‌اندازی، ساختار کد، توضیح جریان‌ها (کاربر/ادمین)، تنظیمات و عملیات روزمره است تا ادامه توسعه/پشتیبانی بدون ابهام انجام شود.

---

## 1) خلاصه و هدف محصول
MarzbanSudo یک ربات تلگرامی (aiogram v3) است که فروش و مدیریت اشتراک VPN مبتنی بر Marzban را فراهم می‌کند. ویژگی‌های کلیدی:
- لیست پلن‌ها، خرید از «کیف پول» داخلی، Provision خودکار در Marzban و ارسال لینک‌های اشتراک به کاربر
- شارژ کیف پول با آپلود عکس رسید (کارت‌به‌کارت – بدون کپشن)، تایید/رد توسط ادمین به‌صورت Inline
- نمایش وضعیت اکانت (حجم/مصرف/باقی‌مانده/انقضا) و لینک‌های sub4me
- کنترل‌های ادمین روی کاربران و صف‌ها (Approve/Reject)

---

## 2) پشته فناوری و وابستگی‌ها
- Python 3.11، aiogram v3، httpx، SQLAlchemy 2 (async) + asyncmy، Alembic
- پایگاه‌داده: MariaDB 10.11/ MySQL 8
- Docker + Compose برای اجرا

فایل requirements.txt نسخه دقیق کتابخانه‌ها را مشخص کرده است.

---

## 3) ساختار مخزن و فایل‌های مهم
```
app/
  main.py                 # نقطه ورود ربات (polling)
  logging_config.py       # لاگ ساختاریافته/فایل
  healthcheck.py          # چک سلامت (توکن تلگرام + DB)
  config.py               # بارگیری تنظیمات از env (در حال استفاده محدود)
  bot/
    handlers/
      start.py            # /start و منوی نقش‌محور (کاربر/ادمین)
      plans.py            # لیست پلن‌ها با صفحه‌بندی + خرید از کیف پول
      account.py          # نمایش وضعیت اکانت با قالب‌بندی دو رقمی و دکمه Refresh
      orders.py           # لیست سفارش‌های اخیر (Read-only)
      admin.py            # (اختیاری/تاریخی) ورودی‌های ادمین
      admin_manage.py     # دستورات ا��مین برای کاربر/Marzban (create/delete/reset/...)
      admin_orders.py     # صف سفارش‌های pending (Approve/Reject)
      wallet.py           # کیف پول: شارژ با عکس، مبالغ پیش‌فرض/دلخواه، تایید/رد ادمین
    middlewares/
      rate_limit.py       # محدودیت نرخ پیام کاربر
  db/
    models.py             # ORM: User/Plan/Order/WalletTopUp/Setting/Transaction/AuditLog
    session.py            # اتصال async + session_scope()
    migrations/           # Alembic (env.py, versions/*)
  services/
    marzban_ops.py        # عملیات ایمن Marzban (UI-safe)
    provisioning.py       # Provision تریال و کمک‌تابع‌ها
    scheduler.py          # (اسکلت) کارهای زمان‌بندی‌شده
    audit.py              # ثبت لاگ ممیزی (AuditLog)
  marzban/
    client.py             # کلاینت httpx با دریافت توکن و retry محدود
scripts/
  # ابزارها/اسکریپت‌های جانبی
Dockerfile, docker-compose.yml, alembic.ini
README.md, Roadmap.md, changelog.md, Info.md (این فایل)
```

---

## 4) نصب و اجرا (Production/Staging)
پیش‌نیازها: Docker/Compose، MariaDB/MySQL، Marzban 0.8.4 قابل دسترس با HTTPS.

- تنظیم .env بر اساس .env.example (در مسیر پروفایل)
- اجرای مهاجرت‌ها در استارتاپ ربات با Compose پیکربندی شده است:
  - `command: sh -c "alembic upgrade head && python -m app.main"`
- اجرای سرویس:
```
./update.sh   # یا:
docker compose up -d --build --no-deps bot
```
- اجرای دستی مهاجرت (در صورت نیاز):
```
docker compose exec bot alembic upgrade head
```

سلامت:
- healthcheck از DB و توکن تلگرام اطمینان می‌دهد. لاگ‌ها را در Compose بررسی کنید.

---

## 5) تنظیمات محیطی (ENV)
کلیدهای حیاتی:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_ADMIN_IDS=111111111,222222222
- DB_URL=mysql+asyncmy://sudo_user:PASS@db:3306/marzban_sudo?charset=utf8mb4
- MARZBAN_BASE_URL=https://<panel>
- MARZBAN_ADMIN_USERNAME, MARZBAN_ADMIN_PASSWORD
- SUB_DOMAIN_PREFERRED=irsub.fun
- RATE_LIMIT_USER_MSG_PER_MIN=20
- (Wallet) MIN_TOPUP_IRR (کمینه شارژ به ریال؛ نمایش به تومان)

یادداشت: در پیام‌ها همه مبالغ به تومان نمایش داده می‌شود (IRR/10)، اما در DB به ریال ذخیره می‌گردد.

---

## 6) دیتامدل – کلیدها
- User: telegram_id، marzban_username (tg_<id>)، subscription_token، balance (ریال)، expire_at، data_limit_bytes ...
- Plan: template_id، title، price (ریال)، duration_days، data_limit_bytes ...
- Order: user_id، plan_id، status(pending/paid/provisioned/failed)، amount، provider(wallet|...)
- WalletTopUp: user_id، amount(IRR)، status(pending/approved/rejected)، receipt_file_id، admin_id، timestamps
- Setting: key/value (مثلاً MIN_TOPUP_IRR)
- AuditLog: actor/admin/system/user، action، target_type/id، meta

Migrations تحت app/db/migrations نگهداری می‌شوند. نسخه اخیر: 20250829_000002_wallet.py.

---

## 7) جریان‌های کاربر
- Start و منو:
  - تشخیص نقش (ادمین/کاربر) و نمایش کیبورد مناسب.
- پلن‌ها (🛒):
  - لیست صفحه‌بندی‌شده با Buy (Inline). قیمت از plans گرفته می‌شود.
  - Buy: اگر موجودی کافی نباشد → راهنمای شارژ کیف پول. در غیر این‌صورت: کسر موجودی، ایجاد Order، Provision خودکار و ارسال لینک‌ها.
- کیف پول (💳):
  - نمایش موجودی (تومان)، مبالغ پیش‌فرض (تومان) + دکمه «مبلغ دلخواه»
  - «مبلغ دلخواه»: کاربر عدد تومان ارسال می‌کند (فقط رقم؛ مثل 76000)
  - سپس ربات درخواست عکس/فایل می‌دهد؛ با ارسال، WalletTopUp(pending) ثبت و برای ادمین‌ها ارسال می‌شود.
- سفارش‌ها (📦):
  - فقط لیست آخرین 10 سفارش کاربر (Read-only).
- اکانت (👤):
  - نمایش حجم‌ها با دو رقم اعشار و لینک‌های sub4me؛ دکمه Refresh داخل پیام (کال‌بک قابل پیاده‌سازی).

---

## 8) جریان‌های ادمین
- سفارش‌های در انتظار (🧾):
  - Approve/Reject (idempotent). روی Approve، Provision UI-safe اجرا می‌شود؛ روی Reject وضعیت failed.
- شارژ کیف پول (TopUp):
  - ربات عکس کاربر را با دکمه‌های Approve/Reject برای ادمین می‌فرستد.
  - Approve: افزایش موجودی کاربر (برحسب ریال)، پیام موجودی جدید به تومان برای کاربر
  - Reject: پیام رد به کاربر + درج Rejected در caption ادمین
- کنترل‌های کیف پول:
  - /admin_wallet_set_min <AMOUNT_IRR>
  - /admin_wallet_balance <username> (نمایش به تومان)
  - /admin_wallet_add <username> <amount_IRR>
- کنترل‌های Marzban:
  - /admin_create, /admin_delete, /admin_reset, /admin_revoke, /admin_set ...

نکات ا��منی:
- جلوگیری از سرریز ستون balance قبل از تایید شارژهای خیلی بزرگ
- ACL ادمین با TELEGRAM_ADMIN_IDS

---

## 9) توسعه و استانداردها
- Python 3.11، typing اجباری، SQLAlchemy 2 ORM، الگوی session_scope()
- پیام‌ها و کیبوردها با aiogram v3 (Router-based)
- لاگ ساختاریافته JSON؛ در production سطح INFO
- Migrations: فقط مسیر app/db/migrations معتبر است؛ نسخه‌های stray را حذف/نادیده بگیرید.
- واحد پول: ذخیره داخلی ریال، نمایش تومان

کامیت‌ها و مستندسازی:
- هر تغییر مهم در changelog.md مستند شود
- Roadmap.md مرجع معماری و Runbook است؛ Info.md راهنمای عملیاتی سریع

---

## 10) راهنمای عیب‌یابی
- خطای ستون balance → اجرای Alembic در مسیر صحیح (app/db/migrations)
- BadRequest در ویرایش پیام ادمین → برای عکس/فایل از edit_caption استفاده کنید
- 409 روی ساخت کاربر Marzban → مسیر UI-safe (create → PUTs) استفاده شده؛ لاگ‌ها را بررسی کنید
- موجودی کافی نیست در خرید → از 💳 کیف پول شارژ کنید؛ سپس Buy مجدد

---

## 11) چک‌لیست واگذاری
- [ ] .env کامل روی سرور و مخفی نگه‌داشته شود؛ TELEGRAM_ADMIN_IDS تنظیم شده باشد
- [ ] DB و Alembic up-to-date (alembic upgrade head)
- [ ] SUB_DOMAIN_PREFERRED مقداردهی شده باشد
- [ ] دسترسی ادمین به گروه/چت ادمین برای دریافت شارژها
- [ ] سناریوهای زیر تست شده باشد:
  - شارژ کیف پول (مبلغ پیش‌فرض + دلخواه) → Approve/Reject
  - خرید از موجودی و Provision → دریافت لینک‌ها
  - /account نمایش و Refresh (در صورت پیاده‌سازی کال‌بک)
  - /admin_* دستورات مدیریت کاربر

---

## 12) برنامه‌های بعدی (High-level)
- صورتحساب داخلی برای شارژ (Invoice) + شناسه پیگیری
- صفحه‌بندی صف‌های ادمین و گزارش‌های کیف پول
- افزایش precision ستون balance (در صورت نیاز) به Numeric(18,2)
- i18n پیام‌ها (fa/en) و واحد پولی قابل تنظیم
- Providerهای پرداخت آنلاین (NowPayments/aqayepardakht) به‌صورت افزونه‌ای

---

## 13) ارجاعات
- Roadmap.md: مشخصات کامل معماری/Runbook/Backlog
- changelog.md: جزئیات تغییرات سیر زمانی
- app/marzban/client.py: نگاشت APIهای Marzban
