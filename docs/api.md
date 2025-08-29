# Marzban 0.8.4 – API Quick Reference & Curl Recipes (Curated)

این سند خلاصه‌ای عملی از APIهای Marzban است که در پروژه MarzbanSudo استفاده می‌شوند، به‌همراه نمونه‌های امن curl، الگوهای پاسخ، نکات خطا و رفع اشکال. نمونه‌ها از متغیرهای محیطی و جای‌نگهدارها استفاده می‌کنند تا از افشای اطلاعات جلوگیری شود.


## 1) مبانی و احراز هویت
- Base URL (HTTPS ضروری):
  - مثال: https://panel.example.com
  - در نمونه‌ها از $BASE استفاده می‌کنیم:
    - export BASE="https://panel.example.com"
- احراز ادمین (Token):
  - Endpoint: POST /api/admin/token
  - Content-Type: application/x-www-form-urlencoded
  - Body: grant_type=password&username=<ADMIN>&password=<PASS>
  - Response: { access_token, token_type }

نمون��:
```bash
export ADMIN_USER="your_admin"
export ADMIN_PASS="your_password"
TOKEN=$(curl -sS -X POST "$BASE/api/admin/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password&username=$ADMIN_USER&password=$ADMIN_PASS" | jq -r .access_token)
# تأیید
[ -n "$TOKEN" ] && echo "Token OK" || echo "Token FAILED"
```

همه درخواست‌های محافظت‌شده:
```bash
-H "Authorization: Bearer $TOKEN"
```

نکات امنیتی
- Token را لاگ نکنید و در ترمینال History نگه ندارید.
- حتماً از HTTPS معتبر استفاده کنید.


## 2) Inbounds – دریافت برچسب‌های ورودی قابل استفاده
Bot برای ساخت کاربر به‌صورت UI-safe نیاز به فهرست inbounds دارد تا تگ‌های معتبر را انتخاب کند.
- GET /api/inbounds

نمونه:
```bash
curl -sS "$BASE/api/inbounds" -H "Authorization: Bearer $TOKEN" | jq .
```

نکته: برخی برچسب‌ها مانند "Info" صرفاً نمایشی‌اند و باید حذف شوند.


## 3) User Templates – همگام‌سازی پلن‌ها
- GET /api/user_template → برای sync به جدول plans

نمونه:
```bash
curl -sS "$BASE/api/user_template" -H "Authorization: Bearer $TOKEN" | jq .
```

خروجی نمونه رکورد:
```json
{
  "id": 9,
  "name": "30D-50GB",
  "data_limit": 53687091200,
  "expire_duration": 2592000,
  "inbounds": { "vless": ["VLESS-CDN-ALL", "VLESS+TCP+REALITY"] }
}
```


## 4) Users – مسیر UI-safe برای ساخت/به‌روزرسانی
به‌جای اتکا به template_id (که در برخی نسخه‌ها موجب 500/409 یا اختلال UI می‌شود)، توصیه می‌شود کاربر با payload حداقلی ساخته و محدودیت‌ها در PUT اعمال شوند.

4.1) ساخت کاربر (حداقلی و UI-safe)
- POST /api/user
- Body (JSON):
  - username: tg_<telegram_id>
  - status: active
  - expire: 0, data_limit: 0
  - data_limit_reset_strategy: no_reset
  - inbounds: از GET /api/inbounds مشتق شود (مثلاً فقط vless)
  - proxies: { "vless": {} }

نمونه:
```bash
USERNAME="tg_123456789"
cat > /tmp/user_create.json <<'JSON'
{
  "username": "__USERNAME__",
  "status": "active",
  "expire": 0,
  "data_limit": 0,
  "data_limit_reset_strategy": "no_reset",
  "inbounds": {"vless": ["VLESS-CDN-ALL", "VLESS+TCP+REALITY"]},
  "proxies": {"vless": {}},
  "note": "created by bot"
}
JSON
sed -i "s/__USERNAME__/$USERNAME/" /tmp/user_create.json
curl -sS -X POST "$BASE/api/user" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @/tmp/user_create.json | jq .
```

4.2) تنظیم محدودیت‌ها (حجم/انقضا) پس از ساخت
- PUT /api/user/{username}

نمونه (تنظیم 30 روز و 50GB):
```bash
EXPIRE_TS=$(date -u -d "+30 days" +%s)
DATA_LIMIT=$((50*1024*1024*1024))
curl -sS -X PUT "$BASE/api/user/$USERNAME" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"expire\":$EXPIRE_TS}" | jq .
curl -sS -X PUT "$BASE/api/user/$USERNAME" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"data_limit\":$DATA_LIMIT}" | jq .
```

4.3) بازیابی کاربر
- GET /api/user/{username}

4.4) ریست مصرف و ری‌وُک لینک
- POST /api/user/{username}/reset
- POST /api/user/{username}/revoke_sub

نکات خطا
- 409 Conflict: کاربر وجود دارد → از GET یا PUT استفاده کنید.
- 404 Not Found: نام کاربر درست نیست یا حذف شده است.


## 5) Users – منقضی‌ها
- GET /api/users/expired → فهرست کاربران منقضی
- DELETE /api/users/expired → روی برخی بیلدها 404 می‌دهد؛ در این صورت به‌صورت fallback: GET و سپس DELETE per-user.


## 6) Subscription – sub4me
- GET /sub4me/{token}/ → خروجی بسته به User-Agent و client_type متفاوت است (attachment)
- GET /sub4me/{token}/info → JSON شامل proxies، expire، data_limit، used_traffic، links و subscription_url
- GET /sub4me/{token}/usage → مصرف تفکیکی
- GET /sub4me/{token}/{client_type} → v2ray | v2ray-json | clash | clash-meta | sing-box | outline

نمونه info:
```bash
TOKEN_SUB="<subscription_token>"
curl -sS "$BASE/sub4me/$TOKEN_SUB/info" | jq .
```

خلاصه فیلدهای مهم در info:
- subscription_url: برای نمایش لینک‌های سریع (domain ترجیحی با SUB_DOMAIN_PREFERRED جایگزین می‌شود)
- used_traffic / data_limit / expire: مقیاس و قالب‌بندی در Bot انجام می‌شود


## 7) الگوی کامل Provision (ایمن و سازگار با UI)
1) دریافت inbounds → استخراج برچسب‌های معتبر
2) POST /api/user (payload حداقلی)
3) PUT /api/user/{username} برای expire
4) PUT /api/user/{username} برای data_limit
5) GET /api/user/{username} → دریافت snapshot و token

نکات مهم
- از ارسال template_id در ساخت اولیه اجتناب کنید (برخی نسخه‌ها 500/409 می‌دهند و UI خراب می‌شود).
- staged PUT برای expire و data_limit انجام دهید.


## 8) الگوهای خطا و رفتار پیشنهادی
- 401 Unauthorized: Token منقضی/اشتباه → login مجدد و retry یک‌باره
- 409 Conflict: موجود بودن موجودیت → GET/PUT/DELETE مطابق وضعیت
- 404 Not Found: مسیر/شناسه نادرست یا عدم پشتیبانی endpoint در بیلد جاری
- 422 Validation Error: بدنه/پارامتر اشتباه
- 5xx: Backoff + retry محدود، سپس پیام کاربرپسند و لاگ فنی

نمونه Backoff ساده (bash):
```bash
for i in 1 2 3; do
  http_code=$(curl -sS -o /tmp/resp.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" "$BASE/api/user/$USERNAME")
  [ "$http_code" = 200 ] && break
  sleep $((i*i))
done
cat /tmp/resp.json | jq .
```


## 9) نگاشت به کد پروژه
- app/marzban/client.py → _login(), _request(), backoff محدود
- app/services/marzban_ops.py → create_user_minimal, update_user_limits, revoke/reset, provision_for_plan
- app/scripts/sync_plans.py → GET /api/user_template و نگاشت به plans
- bot/handlers/account.py → GET /sub4me/{token}/info برای نمایش


## 10) رفع اشکال (Troubleshooting)
- 404 روی DELETE /api/users/expired: از fallback per-user ��ستفاده کنید.
- 409 روی POST /api/user: کاربر وجود دارد → مسیر PUT/GET را دنبال کنید.
- 500 روی POST /api/user با template_id: payload حداقلی بدون template_id استفاده کنید و سپس PUTها را اجرا نمایید.
- لینک‌های اشتراک: اگر domain متفاوت می‌خواهید، فقط در سطح نمایش با SUB_DOMAIN_PREFERRED بازنویسی کنید؛ token همان است.
- TLS/HTTPS: خطاهای گواهی را رفع کنید؛ از self-signed در production اجتناب کنید.


## 11) ضمیمه – نمونه Payloadها
ساخت حداقلی کاربر (vless only):
```json
{
  "username": "tg_262182607",
  "status": "active",
  "expire": 0,
  "data_limit": 0,
  "data_limit_reset_strategy": "no_reset",
  "inbounds": {"vless": ["VLESS-CDN-ALL", "VLESS+TCP+REALITY"]},
  "proxies": {"vless": {}},
  "note": "created by bot"
}
```

data_limit/expire (PUT):
```json
{ "expire": 1759301999 }
{ "data_limit": 53687091200 }
```

نمونه پاسخ info:
```json
{
  "proxies": {"vless": {"id": "0750...a29", "flow": "xtls-rprx-vision"}},
  "expire": 1759301999,
  "data_limit": 53687091200,
  "used_traffic": 10896313296,
  "links": ["vless://..."],
  "subscription_url": "https://panel.example.com/sub4me/XXXXXXXX"
}
```


## 12) هشدارها و بهترین‌عمل‌ها
- هرگز access_token یا گذرواژه را در مخزن/issueها قرار ندهید.
- نرخ درخواست‌ها را محدود کنید؛ backoff روی 429/5xx.
- API نسخه 0.8.4 ممکن است در برخی بیلدها تفاوت جزئی داشته باشد؛ کد باید fallback مناسب داشته باشد (مانند expireds delete).
- همه زمان‌ها را UTC نگه دارید؛ تبدیل نمایش با TZ محلی.


## 13) پیوندها
- OpenAPI: $BASE/openapi.json (برای بررسی کامل طرح)
- مستندات پروژه: Info.md (Handover)، Roadmap.md (Spec/Runbook)، changelog.md (تاریخچه)
