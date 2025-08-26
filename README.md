# MarzbanSudo (MVP bootstrap)

گام‌های اجرا:

1) فایل `.env` را بر اساس `.env.example` بسازید و مقادیر را تکمیل کنید (خصوصاً TELEGRAM_BOT_TOKEN).

2) اجرای سرویس‌ها با Docker Compose:
```bash
docker compose up -d --build
```

3) بررسی لاگ‌ها:
```bash
docker logs -f marzban_sudo_bot
```

4) در تلگرام به ربات پیام `/start` بدهید و پاسخ اولیه را دریافت کنید.

ساختار کد به‌صورت مرحله‌ای تکمیل می‌شود. مسیرهای فازها مطابق Roadmap.md: client → ORM/CRUD → Bot flows → Payment → Scheduler.
