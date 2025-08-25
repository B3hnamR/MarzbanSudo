# MarzbanSudo – Roadmap & Spec [1]

این سند نقشه راه، مشخصات فنی، معماری، نگاشت APIهای مرزبان، دیتامدل و فرآیندهای عملیاتی ربات تلگرامی مدیریت/فروش مبتنی بر Marzban 0.8.4 را برای تحویل به تیم توسعه ارائه می‌کند. [1]

---

## اهداف و محدوده [1]
- ساخت ربات تلگرامی فروش/مدیریت که به پنل Marzban متصل است، ساخت/تمدید کاربر، ارسال لینک‌های Subscription و نمایش مصرف/انقضا را انجام می‌دهد. [1]
- پرداخت در فاز اول به‌صورت کارت‌به‌کارت با تایید ادمین و قابل‌تعویض با درگاه در آینده، بدون اجازه Reset مصرف توسط کاربر. [1]
- سیاست تمدید: افزودن حجم به پلان فعلی بدون تغییر تاریخ انقضا؛ خرید پلان جدید یعنی جایگزینی کامل و سوختن باقی‌مانده قبلی. [1]
- مدیریت منقضی‌ها: غیرفعال‌سازی و اعلان تمدید، سپس حذف خودکار بعد از X روز از طریق کران. [1]

## اطلاعات محیط و تنظیمات [1]
- Marzban: MARZBAN_BASE_URL = https://p.v2pro.store ، اکانت ادمین اختصاصی بات: adminbottest. [1]
- Subscription domain: نمایش subscription_url فوروارد‌شده روی irsub.fun برای کاربران. [1]
- کلاینت‌های هدف: iOS: Streisand، Android: v2rayNG، Windows: v2rayN، لینک‌های sub4me همه‌جا ساپورت. [1]
- نام‌گذاری کاربر: tg_<telegram_id> (حروف کوچک، بدون فاصله)، مثال: tg_262182607. [1]
- دیتابیس: MariaDB یا MySQL (پیشنهاد MariaDB 10.11 LTS)، عدم استفاده از SQLite. [1]
- دیپلوی: Docker Compose با سرویس‌های bot و db و volume پایدار. [1]
- توکن ربات: در زمان نصب/روی سرور ست شود (نه داخل ریپو)، امکان rotate از طریق دستور ادمین یا اسکریپت setup. [1]

## معماری سیستم [1]
- Bot Service: aiogram v3 برای هندل پیام‌ها، منوها، نوتیف‌ها، و ACL ادمین. [1]
- Marzban Client: httpx client با احراز هویت ادمین، نگهداری Bearer Token و ری‌لاگین روی 401. [1]
- Database Layer: SQLAlchemy 2 async + asyncmy/aiomysql روی MariaDB/MySQL، با Alembic برای migrations. [1]
- Scheduler/Worker: اجرای کران‌های مصرف/انقضا/پاکسازی سفارش‌ها (asyncio/aiojobs). [1]
- Payment: فاز اول manual_transfer (کارت‌به‌کارت)، بعداً قابل‌تعویض با Zarinpal/IDPay/… بدون تغییر لایه‌های بالایی. [1]

## ساختار پوشه‌ها (ساخته‌شده) [1]
- ریشه: docker/، scripts/، docker-compose.yml، requirements.txt، alembic.ini، .env.example. [1]
- app/: main.py، bootstrap.py، config.py، logging_config.py، utils/، db/، marzban/، services/، payment/، bot/. [1]
- app/db/: base.py، models.py، migrations/ (env.py, versions/)، crud/ (users.py, plans.py, orders.py, transactions.py). [1]
- app/marzban/: client.py، schemas.py. [1]
- app/services/: provisioning.py، billing.py، notifications.py، scheduler.py، security.py. [1]
- app/payment/: manual_transfer.py، providers/ (zarinpal.py، idpay.py) برای آینده. [1]
- app/bot/: handlers/ (start, plans, orders, account, admin)، keyboards/، middlewares/، filters/، callbacks/. [1]

## پیکربندی و ENV [1]
- متغیرها: APP_ENV، TZ، MARZBAN_BASE_URL، MARZBAN_ADMIN_USERNAME، MARZBAN_ADMIN_PASSWORD، TELEGRAM_BOT_TOKEN، TELEGRAM_ADMIN_IDS، DB_URL، NOTIFY_USAGE_THRESHOLDS، NOTIFY_EXPIRY_DAYS، SUB_DOMAIN_PREFERRED، LOG_CHAT_ID. [1]
- TOKEN ربات هنگام نصب از ادمین دریافت و در .env سرور ذخیره شود، با امکان چرخش امن و ری‌استارت سرویس. [1]

## نگاشت فیچرها به API Marzban [1]
- احراز ادمین: POST /api/admin/token → دریافت access_token bearer. [1]
- قالب‌ها/پلن‌ها: GET /api/user_template و GET /api/user_template/{id} برای sync با جدول plans داخلی. [1]
- ساخت کاربر: POST /api/user با username و template_id و override فیلدهای data_limit و expire (template فعلی id=1 و مقادیر پیش‌فرض 0 است). [1]
- دریافت کاربر: GET /api/user/{username} → گرفتن proxies, inbounds, subscription_url, expire, usage base. [1]
- افزایش حجم/تمدید: PUT /api/user/{username} با مقدار جدید data_limit (جمع مقدار فعلی + خرید جدید). [1]
- ریست مصرف: POST /api/user/{username}/reset (در سیاست فعلی برای کاربر مجاز نیست؛ فقط ادمین در “جایگزینی کامل”). [1]
- چرخش لینک: POST /api/user/{username}/revoke_sub در صورت نیاز امنیتی یا جایگزینی پلن. [1]
- Next plan: POST /api/user/{username}/active-next فقط زمانی که next_plan تعریف شده باشد (فعلاً نیاز نداریم). [1]
- مصرف و لینک‌ها برای کاربر: GET /sub4me/{token}/info و /usage و لینک‌های client_type مثل /v2ray و /v2ray-json. [1]
- منقضی‌ها: GET /api/users/expired و DELETE /api/users/expired برای پاکسازی دوره‌ای. [1]

## سناریوهای عملیاتی [1]
- نام‌گذاری: tg_<telegram_id> هنگام Provision و یکتا بر اساس Telegram ID. [1]
- خرید اولیه: ساخت Order(pending) → پرداخت کارت‌به‌کارت → تایید ادمین → ساخت/آپدیت کاربر → ارسال subscription_url و لینک‌های مخصوص کلاینت. [1]
- افزودن حجم (تمدید): GET user → محاسبه new_limit = current.data_limit + added_bytes → PUT user با data_limit=new_limit. [1]
- خرید پلان جدید (جایگزینی کامل): PUT user با data_limit و expire جدید + POST reset + POST revoke_sub (اختیاری امنیتی). [1]
- اعلان‌ها: مصرف 70%/90%، انقضا 3/1/0 روز، پیام‌های راهنما و هشدارهای لازم. [1]

## دیتامدل (ORM) [1]
- users: telegram_id, marzban_username, subscription_token, status, expire_at, data_limit_bytes, created_at. [1]
- plans: title, price, currency, template_id, duration_days, data_limit_bytes, description. [1]
- orders: user_id, plan_id, status(pending|paid|provisioned|failed), amount, provider(manual_transfer), provider_ref, idempotency_key, created_at. [1]
- transactions: invoice_id, status, payload_raw, signature_valid, created_at. [1]
- audit_logs: actor, action, target, meta, created_at. [1]

## فلوهای ربات تلگرام [1]
- کاربر عادی: /start، مشاهده پلن‌ها، ایجاد سفارش، ارسال اطلاعات کارت‌به‌کارت/آپلود رسید، دریافت لینک‌های ساب، مشاهده مصرف/انقضا. [1]
- اکانت من: نمایش وضعیت، subscription_url، لینک‌های ویژه کلاینت‌ها، مصرف (sub4me/usage)، بدون Reset مصرف. [1]
- ادمین: تایید/رد سفارش‌ها، جستجوی کاربر، revoke_sub، گزارش خطا/رخداد در LOG_CHAT_ID، مدیریت قیمت‌ها/پلن‌ها. [1]

## امنیت و عملیات [1]
- ادمین Marzban اختصاصی برای بات با کمترین سطح دسترسی و تغییر دوره‌ای پسورد/توکن. [1]
- ذخیره امن Secrets در .env سرور، Rate-limit در بات، لاگ‌برداری بدون اطلاعات حساس، بررسی صحت ورودی‌ها. [1]
- دیپلوی ایزوله با Docker، محدودسازی خروجی کانتینر بات به آدرس‌های مورد نیاز (Marzban و پرداخت). [1]
- پایش خطاها (4xx/5xx) و آلارم داخلی به کانال/گروه ادمین. [1]

## مثال‌های API کاربردی [1]
- ساخت کاربر جدید با template_id=1 و override حجم/انقضا: [1]
  - data_limit برحسب بایت (مثلاً 50GB = 53687091200)، expire یونیکس ثانیه (اکنون + 30 روز). [1]


POST /api/user HTTP/1.1 (Authorization: Bearer <token>)
{
"username": "tg_262182607",
"template_id": 1,
"data_limit": 53687091200,
"expire": 1759301999,
"note": "plan: 50GB/30d"
}

[1]

- دریافت اطلاعات کاربر و subscription_url: [1]
GET /api/user/tg_262182607 HTTP/1.1 (Authorization: Bearer <token>)

[1]

- افزودن حجم (تمدید): [1]


PUT /api/user/tg_262182607 HTTP/1.1 (Authorization: Bearer <token>)
{ "data_limit": <new_limit_bytes> }


[1]

- لینک‌های ساب برای کلاینت‌ها (با token از GET user/info): [1]
  - عمومی: https://irsub.fun/sub4me/{token}/ [1]
  - v2ray/v2rayN/v2rayNG: https://irsub.fun/sub4me/{token}/v2ray [1]
  - JSON: https://irsub.fun/sub4me/{token}/v2ray-json [1]

## پرداخت کارت‌به‌کارت (MVP) [1]
- ایجاد Order با status=pending و نمایش مبلغ، کارت مقصد (نام بانک، چهار رقم آخر، نام صاحب کارت)، راهنمای ارسال رسید. [1]
- کاربر آپلود رسید/اطلاعات تراکنش → صف بررسی ادمین در تلگرام → تایید/رد. [1]
- روی تایید: Provision (ساخت/آپدیت کاربر طبق سیاست تمدید/جایگزینی) → ارسال subscription_url و لینک‌های کلاینت. [1]
- Idempotency: قفل روی idempotency_key/order_id برای جلوگیری از Provision تکراری. [1]

## نوتیفیکیشن‌ها [1]
- مصرف: ارسال هشدار در آستانه 70% و 90% برای کاربران. [1]
- انقضا: یادآوری در 3 روز، 1 روز و روز صفر پیش از پایان اعتبار. [1]
- ادمین: گزارش سفارش‌های جدید/تایید شده/رد شده، و خطاهای سرویس. [1]

## فازبندی اجرا [1]
- فاز 0: آماده‌سازی زیرساخت (Docker, DB, .env)، ساخت ادمین اختصاصی مرزبان برای بات و اعتبارسنجی اتصال. [1]
- فاز 1: پیاده‌سازی Marzban Client و Auth، Wrapper endpoints: token, user_template, user, sub4me. [1]
- فاز 2: دیتامدل و CRUD، همگام‌سازی Templateها با plans داخلی (قیمت/عنوان قابل override). [1]
- فاز 3: اسکلت ربات (start/plans/orders/account) با Polling برای MVP. [1]
- فاز 4: پرداخت کارت‌به‌کارت، صف تایید ادمین، Provision end-to-end و پیام‌های کاربر. [1]
- فاز 5: Scheduler اعلان‌ها و مدیریت Expiredها و پاکسازی دوره‌ای. [1]
- فاز 6: امنیت/لاگ/مانیتورینگ و سخت‌سازی دسترسی‌ها و چرخش توکن‌ها. [1]
- فاز 7: تست نهایی، مستندسازی، و آماده‌سازی برای افزودن درگاه‌های پرداخت و انتخاب سرور. [1]

## معیارهای پذیرش (Acceptance) [1]
- ساخت یوزر جدید و ارسال subscription_url و لینک‌های v2ray/v2ray-json از طریق ربات. [1]
- تمدید با افزودن حجم بدون تغییر expire و نمایش صحیح مصرف/انقضا از sub4me/info. [1]
- پرداخت دستی با تایید ادمین و Provision idempotent بدون خطای تکراری. [1]
- اعلان‌های مصرف/انقضا در بازه‌های تعریف‌شده و لاگ رخدادها برای ادمین. [1]

## نکات اجرایی مهم [1]
- template_id اولیه = 1 (my template 1) با data_limit و expire صفر؛ حین ساخت یوزر باید override شوند. [1]
- active-next فقط وقتی next_plan موجود است؛ در سیاست فعلی استفاده نمی‌شود. [1]
- Reset مصرف برای کاربر مجاز نیست؛ فقط در سناریوی جایگزینی کامل توسط ادمین. [1]
- نمایش subscription_url بر پایه دامنه فوروارد شده irsub.fun برای تجربه کاربری بهتر. [1]

## مسیر پروژه [1]
- C:\Users\Behnam\Documents\GitHub\MarzbanSudo (ایجاد‌شده با اسکریپت) و آماده دریافت کدهای هر ماژول طبق فازبندی. [1]


