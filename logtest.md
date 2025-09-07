[+] Building 2/2
 ✔ marzbansudo-bot     Built                                      0.0s 
 ✔ marzbansudo-worker  Built                                      0.0s 
[*] Run DB migrations...
WARN[0000] /opt/MarzbanSudo/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Creating 1/1
 ✔ Container marzban_sudo_db  Runn...                             0.0s 
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
[*] Recreate bot...
WARN[0000] /opt/MarzbanSudo/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 1/1
 ✔ Container marzban_sudo_bot  St...                              9.2s 
[*] Recreate worker...
WARN[0000] /opt/MarzbanSudo/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 1/1
 ✔ Container marzban_sudo_worker  Started                        10.7s 
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[*] waiting for worker to become healthy... (status=starting)
[!] worker not healthy after 30s (status=starting), continuing anyway
[*] Tail logs (bot) — Ctrl+C to exit
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
{"level": "INFO", "time": "2025-09-07T17:39:47+0330", "logger": "app.logging_config", "message": "logging configured", "env": "production", "format": "json", "to_file": false, "file": null}
{"level": "INFO", "time": "2025-09-07T17:39:47+0330", "logger": "root", "message": "Starting Telegram bot polling ..."}
{"level": "INFO", "time": "2025-09-07T17:39:47+0330", "logger": "aiogram.dispatcher", "message": "Start polling"}
{"level": "INFO", "time": "2025-09-07T17:39:47+0330", "logger": "aiogram.dispatcher", "message": "Run polling for bot @V2PROTestBot id=8458475411 - 'V2PRO TEST'"}
{"level": "INFO", "time": "2025-09-07T17:43:34+0330", "logger": "aiogram.event", "message": "Update id=618064294 is handled. Duration 354 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:06+0330", "logger": "aiogram.event", "message": "Update id=618064295 is handled. Duration 297 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:08+0330", "logger": "aiogram.event", "message": "Update id=618064296 is handled. Duration 59 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:10+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/admin/token \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:44:10+0330", "logger": "root", "message": "Marzban token acquired"}
{"level": "INFO", "time": "2025-09-07T17:44:10+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg2621826078bf \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:44:10+0330", "logger": "aiogram.event", "message": "Update id=618064297 is handled. Duration 510 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:14+0330", "logger": "aiogram.event", "message": "Update id=618064298 is handled. Duration 70 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:15+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg262182607cet \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:44:15+0330", "logger": "aiogram.event", "message": "Update id=618064299 is handled. Duration 145 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:18+0330", "logger": "aiogram.event", "message": "Update id=618064300 is handled. Duration 70 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:19+0330", "logger": "aiogram.event", "message": "Update id=618064301 is handled. Duration 49 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:21+0330", "logger": "aiogram.event", "message": "Update id=618064302 is handled. Duration 168 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:25+0330", "logger": "app.bot.handlers.wallet", "message": "wallet topup created", "cid": "ce36487f35224755bc76e733457719e8", "topup_id": 3, "user_id": 1, "amount_irr": "2500000", "mime": "photo"}
{"level": "INFO", "time": "2025-09-07T17:44:25+0330", "logger": "aiogram.event", "message": "Update id=618064303 is handled. Duration 138 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:26+0330", "logger": "aiogram.event", "message": "Update id=618064304 is handled. Duration 392 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:28+0330", "logger": "aiogram.event", "message": "Update id=618064305 is handled. Duration 90 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:29+0330", "logger": "aiogram.event", "message": "Update id=618064306 is handled. Duration 159 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:33+0330", "logger": "aiogram.event", "message": "Update id=618064307 is handled. Duration 78 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:36+0330", "logger": "app.bot.handlers.wallet", "message": "wallet topup created", "cid": "8ab04884e0c54fab94ff86310906e2d8", "topup_id": 4, "user_id": 1, "amount_irr": "10000000", "mime": "photo"}
{"level": "INFO", "time": "2025-09-07T17:44:36+0330", "logger": "aiogram.event", "message": "Update id=618064308 is handled. Duration 147 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:44:41+0330", "logger": "aiogram.event", "message": "Update id=618064309 is handled. Duration 158 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:05+0330", "logger": "aiogram.event", "message": "Update id=618064310 is handled. Duration 345 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:07+0330", "logger": "aiogram.event", "message": "Update id=618064311 is handled. Duration 89 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:08+0330", "logger": "aiogram.event", "message": "Update id=618064312 is handled. Duration 82 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:09+0330", "logger": "aiogram.event", "message": "Update id=618064313 is handled. Duration 77 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:11+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:12+0330", "logger": "aiogram.event", "message": "Update id=618064314 is handled. Duration 987 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:14+0330", "logger": "aiogram.event", "message": "Update id=618064315 is handled. Duration 55 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:21+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:45:21+0330", "logger": "aiogram.event", "message": "Update id=618064316 is handled. Duration 138 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:44+0330", "logger": "aiogram.event", "message": "Update id=618064317 is handled. Duration 219 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:46+0330", "logger": "aiogram.event", "message": "Update id=618064318 is handled. Duration 104 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:50+0330", "logger": "aiogram.event", "message": "Update id=618064319 is handled. Duration 107 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:54+0330", "logger": "aiogram.event", "message": "Update id=618064320 is handled. Duration 93 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:45:58+0330", "logger": "aiogram.event", "message": "Update id=618064321 is handled. Duration 143 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:46:02+0330", "logger": "app.bot.handlers.wallet", "message": "wallet topup created", "cid": "18437a449dda4ce08f55e65cf7b92266", "topup_id": 5, "user_id": 1, "amount_irr": "514970", "mime": "photo"}
{"level": "INFO", "time": "2025-09-07T17:46:02+0330", "logger": "aiogram.event", "message": "Update id=618064322 is handled. Duration 141 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:46:04+0330", "logger": "aiogram.event", "message": "Update id=618064323 is handled. Duration 315 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:46:51+0330", "logger": "aiogram.event", "message": "Update id=618064324 is handled. Duration 125 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:46:53+0330", "logger": "aiogram.event", "message": "Update id=618064325 is handled. Duration 122 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:03+0330", "logger": "aiogram.event", "message": "Update id=618064326 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:06+0330", "logger": "aiogram.event", "message": "Update id=618064327 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:08+0330", "logger": "aiogram.event", "message": "Update id=618064328 is handled. Duration 65 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:13+0330", "logger": "aiogram.event", "message": "Update id=618064329 is handled. Duration 97 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:14+0330", "logger": "aiogram.event", "message": "Update id=618064330 is handled. Duration 98 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:15+0330", "logger": "aiogram.event", "message": "Update id=618064331 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:25+0330", "logger": "aiogram.event", "message": "Update id=618064332 is handled. Duration 143 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:30+0330", "logger": "aiogram.event", "message": "Update id=618064333 is handled. Duration 70 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:47:42+0330", "logger": "aiogram.event", "message": "Update id=618064334 is handled. Duration 56 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:25+0330", "logger": "aiogram.event", "message": "Update id=618064335 is handled. Duration 205 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:27+0330", "logger": "aiogram.event", "message": "Update id=618064336 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:28+0330", "logger": "aiogram.event", "message": "Update id=618064337 is handled. Duration 85 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:30+0330", "logger": "aiogram.event", "message": "Update id=618064338 is handled. Duration 262 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:33+0330", "logger": "aiogram.event", "message": "Update id=618064339 is handled. Duration 53 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:34+0330", "logger": "aiogram.event", "message": "Update id=618064340 is handled. Duration 73 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:35+0330", "logger": "aiogram.event", "message": "Update id=618064341 is handled. Duration 105 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:36+0330", "logger": "aiogram.event", "message": "Update id=618064342 is handled. Duration 97 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:37+0330", "logger": "aiogram.event", "message": "Update id=618064343 is handled. Duration 78 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:43+0330", "logger": "aiogram.event", "message": "Update id=618064344 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:44+0330", "logger": "aiogram.event", "message": "Update id=618064345 is handled. Duration 225 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:46+0330", "logger": "aiogram.event", "message": "Update id=618064346 is handled. Duration 142 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:47+0330", "logger": "aiogram.event", "message": "Update id=618064347 is handled. Duration 84 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:48+0330", "logger": "aiogram.event", "message": "Update id=618064348 is handled. Duration 169 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:49+0330", "logger": "aiogram.event", "message": "Update id=618064349 is handled. Duration 77 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:50+0330", "logger": "aiogram.event", "message": "Update id=618064350 is handled. Duration 216 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:51+0330", "logger": "aiogram.event", "message": "Update id=618064351 is handled. Duration 219 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:54+0330", "logger": "aiogram.event", "message": "Update id=618064352 is handled. Duration 59 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:55+0330", "logger": "aiogram.event", "message": "Update id=618064353 is handled. Duration 91 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:56+0330", "logger": "aiogram.event", "message": "Update id=618064354 is handled. Duration 145 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:57+0330", "logger": "aiogram.event", "message": "Update id=618064355 is handled. Duration 60 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:48:58+0330", "logger": "aiogram.event", "message": "Update id=618064356 is handled. Duration 89 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:01+0330", "logger": "aiogram.event", "message": "Update id=618064357 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:02+0330", "logger": "aiogram.event", "message": "Update id=618064358 is handled. Duration 208 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:04+0330", "logger": "aiogram.event", "message": "Update id=618064359 is handled. Duration 106 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:05+0330", "logger": "aiogram.event", "message": "Update id=618064360 is handled. Duration 245 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:06+0330", "logger": "aiogram.event", "message": "Update id=618064361 is handled. Duration 330 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:07+0330", "logger": "aiogram.event", "message": "Update id=618064362 is handled. Duration 152 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:08+0330", "logger": "aiogram.event", "message": "Update id=618064363 is handled. Duration 90 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg_8393184061 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:10+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:11+0330", "logger": "aiogram.event", "message": "Update id=618064364 is handled. Duration 493 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:28+0330", "logger": "aiogram.event", "message": "Update id=618064365 is handled. Duration 175 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:29+0330", "logger": "aiogram.event", "message": "Update id=618064366 is handled. Duration 154 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:30+0330", "logger": "aiogram.event", "message": "Update id=618064367 is handled. Duration 135 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:34+0330", "logger": "aiogram.event", "message": "Update id=618064368 is handled. Duration 131 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:42+0330", "logger": "aiogram.event", "message": "Update id=618064369 is handled. Duration 55 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:43+0330", "logger": "aiogram.event", "message": "Update id=618064370 is handled. Duration 61 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:45+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:46+0330", "logger": "aiogram.event", "message": "Update id=618064371 is handled. Duration 366 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:52+0330", "logger": "aiogram.event", "message": "Update id=618064372 is handled. Duration 91 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:54+0330", "logger": "aiogram.event", "message": "Update id=618064373 is handled. Duration 131 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:55+0330", "logger": "aiogram.event", "message": "Update id=618064374 is handled. Duration 166 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:56+0330", "logger": "aiogram.event", "message": "Update id=618064375 is handled. Duration 131 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:57+0330", "logger": "aiogram.event", "message": "Update id=618064376 is handled. Duration 130 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:49:59+0330", "logger": "aiogram.event", "message": "Update id=618064377 is handled. Duration 613 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:06+0330", "logger": "aiogram.event", "message": "Update id=618064378 is handled. Duration 123 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:08+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:50:09+0330", "logger": "aiogram.event", "message": "Update id=618064379 is handled. Duration 262 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:15+0330", "logger": "aiogram.event", "message": "Update id=618064380 is handled. Duration 78 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:17+0330", "logger": "aiogram.event", "message": "Update id=618064381 is handled. Duration 52 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:19+0330", "logger": "aiogram.event", "message": "Update id=618064382 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:27+0330", "logger": "aiogram.event", "message": "Update id=618064383 is handled. Duration 141 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:29+0330", "logger": "aiogram.event", "message": "Update id=618064384 is handled. Duration 168 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:31+0330", "logger": "aiogram.event", "message": "Update id=618064385 is handled. Duration 153 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:37+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_start", "uid": 262182607}
{"level": "INFO", "time": "2025-09-07T17:50:37+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_start.cleanup", "uid": 262182607}
{"level": "INFO", "time": "2025-09-07T17:50:37+0330", "logger": "aiogram.event", "message": "Update id=618064386 is handled. Duration 68 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:38+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_ref", "uid": 262182607, "text": "8393184061"}
{"level": "INFO", "time": "2025-09-07T17:50:38+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_ref.stage", "uid": 262182607, "stage": "await_ref"}
{"level": "INFO", "time": "2025-09-07T17:50:38+0330", "logger": "aiogram.event", "message": "Update id=618064387 is handled. Duration 81 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:40+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_unit.enter", "uid": 262182607, "data": "walletadm:add:unit:TMN"}
{"level": "INFO", "time": "2025-09-07T17:50:40+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_unit.choice", "uid": 262182607, "unit": "TMN"}
{"level": "INFO", "time": "2025-09-07T17:50:40+0330", "logger": "aiogram.event", "message": "Update id=618064388 is handled. Duration 96 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:43+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_amount.enter", "uid": 262182607, "text": "5000000"}
{"level": "INFO", "time": "2025-09-07T17:50:43+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_amount.stage", "uid": 262182607, "stage": "await_amount", "unit": "TMN", "user_id": 2}
{"level": "INFO", "time": "2025-09-07T17:50:44+0330", "logger": "aiogram.event", "message": "Update id=618064389 is handled. Duration 154 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:47+0330", "logger": "aiogram.event", "message": "Update id=618064390 is handled. Duration 124 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:50+0330", "logger": "aiogram.event", "message": "Update id=618064391 is handled. Duration 65 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:51+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:50:51+0330", "logger": "aiogram.event", "message": "Update id=618064392 is handled. Duration 146 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:53+0330", "logger": "aiogram.event", "message": "Update id=618064393 is handled. Duration 125 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:56+0330", "logger": "aiogram.event", "message": "Update id=618064394 is handled. Duration 129 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:50:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:50:58+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:50:58+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:50:58+0330", "logger": "aiogram.event", "message": "Update id=618064395 is handled. Duration 280 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:05+0330", "logger": "aiogram.event", "message": "Update id=618064396 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:07+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:51:07+0330", "logger": "aiogram.event", "message": "Update id=618064397 is handled. Duration 523 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:14+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:51:14+0330", "logger": "aiogram.event", "message": "Update id=618064398 is handled. Duration 150 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:15+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:51:15+0330", "logger": "aiogram.event", "message": "Update id=618064399 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:18+0330", "logger": "aiogram.event", "message": "Update id=618064400 is handled. Duration 74 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:23+0330", "logger": "aiogram.event", "message": "Update id=618064401 is handled. Duration 76 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:25+0330", "logger": "aiogram.event", "message": "Update id=618064402 is handled. Duration 101 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:26+0330", "logger": "aiogram.event", "message": "Update id=618064403 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:28+0330", "logger": "aiogram.event", "message": "Update id=618064404 is handled. Duration 104 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:29+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg83931840611v5 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:51:29+0330", "logger": "aiogram.event", "message": "Update id=618064405 is handled. Duration 182 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:31+0330", "logger": "aiogram.event", "message": "Update id=618064406 is handled. Duration 115 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:32+0330", "logger": "aiogram.event", "message": "Update id=618064407 is handled. Duration 213 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:34+0330", "logger": "aiogram.event", "message": "Update id=618064408 is handled. Duration 183 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:41+0330", "logger": "aiogram.event", "message": "Update id=618064409 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:51:42+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:51:42+0330", "logger": "aiogram.event", "message": "Update id=618064410 is handled. Duration 290 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:01+0330", "logger": "aiogram.event", "message": "Update id=618064411 is handled. Duration 128 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:02+0330", "logger": "aiogram.event", "message": "Update id=618064412 is handled. Duration 273 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:03+0330", "logger": "aiogram.event", "message": "Update id=618064413 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:05+0330", "logger": "aiogram.event", "message": "Update id=618064414 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:07+0330", "logger": "aiogram.event", "message": "Update id=618064415 is handled. Duration 118 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:09+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:09+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:09+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:09+0330", "logger": "aiogram.event", "message": "Update id=618064416 is handled. Duration 297 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:15+0330", "logger": "aiogram.event", "message": "Update id=618064417 is handled. Duration 141 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:17+0330", "logger": "aiogram.event", "message": "Update id=618064418 is handled. Duration 57 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:19+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:19+0330", "logger": "aiogram.event", "message": "Update id=618064419 is handled. Duration 158 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:39+0330", "logger": "aiogram.event", "message": "Update id=618064420 is handled. Duration 216 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:40+0330", "logger": "aiogram.event", "message": "Update id=618064421 is handled. Duration 77 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:42+0330", "logger": "aiogram.event", "message": "Update id=618064422 is handled. Duration 276 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:43+0330", "logger": "aiogram.event", "message": "Update id=618064423 is handled. Duration 172 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:43+0330", "logger": "aiogram.event", "message": "Update id=618064424 is handled. Duration 110 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:52:45+0330", "logger": "aiogram.event", "message": "Update id=618064425 is handled. Duration 503 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:49+0330", "logger": "aiogram.event", "message": "Update id=618064426 is handled. Duration 40 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:51+0330", "logger": "aiogram.event", "message": "Update id=618064427 is handled. Duration 72 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:52+0330", "logger": "aiogram.event", "message": "Update id=618064428 is handled. Duration 145 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:53+0330", "logger": "aiogram.event", "message": "Update id=618064429 is handled. Duration 98 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:52:55+0330", "logger": "aiogram.event", "message": "Update id=618064430 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:54:21+0330", "logger": "aiogram.event", "message": "Update id=618064431 is handled. Duration 113 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:54:22+0330", "logger": "aiogram.event", "message": "Update id=618064432 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:54:23+0330", "logger": "aiogram.event", "message": "Update id=618064433 is handled. Duration 93 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:11+0330", "logger": "aiogram.event", "message": "Update id=618064434 is handled. Duration 113 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:14+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:55:14+0330", "logger": "aiogram.event", "message": "Update id=618064435 is handled. Duration 236 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:25+0330", "logger": "aiogram.event", "message": "Update id=618064436 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:27+0330", "logger": "aiogram.event", "message": "Update id=618064437 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:28+0330", "logger": "aiogram.event", "message": "Update id=618064438 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:30+0330", "logger": "aiogram.event", "message": "Update id=618064439 is handled. Duration 210 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:31+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:32+0330", "logger": "aiogram.event", "message": "Update id=618064440 is handled. Duration 959 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:34+0330", "logger": "aiogram.event", "message": "Update id=618064441 is handled. Duration 117 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:35+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:35+0330", "logger": "aiogram.event", "message": "Update id=618064442 is handled. Duration 138 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:37+0330", "logger": "aiogram.event", "message": "Update id=618064443 is handled. Duration 67 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:38+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:55:38+0330", "logger": "aiogram.event", "message": "Update id=618064444 is handled. Duration 127 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:40+0330", "logger": "aiogram.event", "message": "Update id=618064445 is handled. Duration 57 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:55:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:55:42+0330", "logger": "aiogram.event", "message": "Update id=618064446 is handled. Duration 265 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:36+0330", "logger": "aiogram.event", "message": "Update id=618064447 is handled. Duration 164 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:37+0330", "logger": "aiogram.event", "message": "Update id=618064448 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:39+0330", "logger": "aiogram.event", "message": "Update id=618064449 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:40+0330", "logger": "aiogram.event", "message": "Update id=618064450 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:42+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:43+0330", "logger": "aiogram.event", "message": "Update id=618064451 is handled. Duration 1323 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:44+0330", "logger": "aiogram.event", "message": "Update id=618064452 is handled. Duration 57 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:46+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:46+0330", "logger": "aiogram.event", "message": "Update id=618064453 is handled. Duration 130 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:48+0330", "logger": "aiogram.event", "message": "Update id=618064454 is handled. Duration 60 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:50+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:50+0330", "logger": "aiogram.event", "message": "Update id=618064455 is handled. Duration 124 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:52+0330", "logger": "aiogram.event", "message": "Update id=618064456 is handled. Duration 128 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:53+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:56:53+0330", "logger": "aiogram.event", "message": "Update id=618064457 is handled. Duration 162 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:56+0330", "logger": "aiogram.event", "message": "Update id=618064458 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:57+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:56:57+0330", "logger": "aiogram.event", "message": "Update id=618064459 is handled. Duration 212 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:56:58+0330", "logger": "aiogram.event", "message": "Update id=618064460 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:03+0330", "logger": "aiogram.event", "message": "Update id=618064461 is handled. Duration 99 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:04+0330", "logger": "aiogram.event", "message": "Update id=618064462 is handled. Duration 87 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:05+0330", "logger": "aiogram.event", "message": "Update id=618064463 is handled. Duration 153 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:07+0330", "logger": "aiogram.event", "message": "Update id=618064464 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:09+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061rvj \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:57:09+0330", "logger": "aiogram.event", "message": "Update id=618064465 is handled. Duration 138 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:13+0330", "logger": "aiogram.event", "message": "Update id=618064466 is handled. Duration 65 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:14+0330", "logger": "aiogram.event", "message": "Update id=618064467 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:34+0330", "logger": "aiogram.event", "message": "Update id=618064468 is handled. Duration 250 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:37+0330", "logger": "aiogram.event", "message": "Update id=618064469 is handled. Duration 291 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:38+0330", "logger": "aiogram.event", "message": "Update id=618064470 is handled. Duration 130 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:57:41+0330", "logger": "aiogram.event", "message": "Update id=618064471 is handled. Duration 485 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:15+0330", "logger": "aiogram.event", "message": "Update id=618064472 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:16+0330", "logger": "aiogram.event", "message": "Update id=618064473 is handled. Duration 101 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:17+0330", "logger": "aiogram.event", "message": "Update id=618064474 is handled. Duration 146 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:22+0330", "logger": "aiogram.event", "message": "Update id=618064475 is handled. Duration 75 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:24+0330", "logger": "aiogram.event", "message": "Update id=618064476 is handled. Duration 98 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:25+0330", "logger": "aiogram.event", "message": "Update id=618064477 is handled. Duration 177 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:26+0330", "logger": "aiogram.event", "message": "Update id=618064478 is handled. Duration 100 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:27+0330", "logger": "aiogram.event", "message": "Update id=618064479 is handled. Duration 212 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:28+0330", "logger": "aiogram.event", "message": "Update id=618064480 is handled. Duration 139 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:29+0330", "logger": "aiogram.event", "message": "Update id=618064481 is handled. Duration 90 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:30+0330", "logger": "aiogram.event", "message": "Update id=618064482 is handled. Duration 100 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:31+0330", "logger": "aiogram.event", "message": "Update id=618064483 is handled. Duration 210 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:32+0330", "logger": "aiogram.event", "message": "Update id=618064484 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:36+0330", "logger": "aiogram.event", "message": "Update id=618064485 is handled. Duration 74 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:38+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:58:38+0330", "logger": "aiogram.event", "message": "Update id=618064486 is handled. Duration 148 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:40+0330", "logger": "aiogram.event", "message": "Update id=618064487 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:41+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:58:41+0330", "logger": "aiogram.event", "message": "Update id=618064488 is handled. Duration 98 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:43+0330", "logger": "aiogram.event", "message": "Update id=618064489 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:44+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:58:44+0330", "logger": "aiogram.event", "message": "Update id=618064490 is handled. Duration 151 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:45+0330", "logger": "aiogram.event", "message": "Update id=618064491 is handled. Duration 54 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:46+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:58:47+0330", "logger": "aiogram.event", "message": "Update id=618064492 is handled. Duration 97 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:58:50+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:58:50+0330", "logger": "aiogram.event", "message": "Update id=618064493 is handled. Duration 104 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:03+0330", "logger": "aiogram.event", "message": "Update id=618064494 is handled. Duration 104 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:04+0330", "logger": "aiogram.event", "message": "Update id=618064495 is handled. Duration 338 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:05+0330", "logger": "aiogram.event", "message": "Update id=618064496 is handled. Duration 101 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:06+0330", "logger": "aiogram.event", "message": "Update id=618064497 is handled. Duration 96 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:07+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061ixp \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T17:59:07+0330", "logger": "aiogram.event", "message": "Update id=618064498 is handled. Duration 183 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:11+0330", "logger": "aiogram.event", "message": "Update id=618064499 is handled. Duration 77 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:13+0330", "logger": "aiogram.event", "message": "Update id=618064500 is handled. Duration 201 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:14+0330", "logger": "aiogram.event", "message": "Update id=618064501 is handled. Duration 253 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:17+0330", "logger": "aiogram.event", "message": "Update id=618064502 is handled. Duration 87 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:18+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061d8a \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:18+0330", "logger": "aiogram.event", "message": "Update id=618064503 is handled. Duration 153 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:18+0330", "logger": "aiogram.event", "message": "Update id=618064504 is handled. Duration 66 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:23+0330", "logger": "aiogram.event", "message": "Update id=618064505 is handled. Duration 111 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:24+0330", "logger": "aiogram.event", "message": "Update id=618064506 is handled. Duration 93 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:26+0330", "logger": "aiogram.event", "message": "Update id=618064507 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:27+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:27+0330", "logger": "aiogram.event", "message": "Update id=618064508 is handled. Duration 143 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:33+0330", "logger": "aiogram.event", "message": "Update id=618064509 is handled. Duration 147 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:35+0330", "logger": "aiogram.event", "message": "Update id=618064510 is handled. Duration 98 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:36+0330", "logger": "aiogram.event", "message": "Update id=618064511 is handled. Duration 85 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:37+0330", "logger": "aiogram.event", "message": "Update id=618064512 is handled. Duration 84 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:39+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061ox4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:39+0330", "logger": "aiogram.event", "message": "Update id=618064513 is handled. Duration 233 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:44+0330", "logger": "aiogram.event", "message": "Update id=618064514 is handled. Duration 97 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:45+0330", "logger": "aiogram.event", "message": "Update id=618064515 is handled. Duration 85 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:46+0330", "logger": "aiogram.event", "message": "Update id=618064516 is handled. Duration 90 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:48+0330", "logger": "aiogram.event", "message": "Update id=618064517 is handled. Duration 69 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:49+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg26218260787e \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:49+0330", "logger": "aiogram.event", "message": "Update id=618064518 is handled. Duration 193 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:50+0330", "logger": "aiogram.event", "message": "Update id=618064519 is handled. Duration 65 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:51+0330", "logger": "aiogram.event", "message": "Update id=618064520 is handled. Duration 145 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:52+0330", "logger": "aiogram.event", "message": "Update id=618064521 is handled. Duration 199 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:53+0330", "logger": "aiogram.event", "message": "Update id=618064522 is handled. Duration 78 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:54+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg2621826078bf \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:54+0330", "logger": "aiogram.event", "message": "Update id=618064523 is handled. Duration 224 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:55+0330", "logger": "aiogram.event", "message": "Update id=618064524 is handled. Duration 162 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:56+0330", "logger": "aiogram.event", "message": "Update id=618064525 is handled. Duration 111 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:57+0330", "logger": "aiogram.event", "message": "Update id=618064526 is handled. Duration 83 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:58+0330", "logger": "aiogram.event", "message": "Update id=618064527 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T17:59:59+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg262182607cet \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T17:59:59+0330", "logger": "aiogram.event", "message": "Update id=618064528 is handled. Duration 229 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:00+0330", "logger": "aiogram.event", "message": "Update id=618064529 is handled. Duration 89 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:02+0330", "logger": "aiogram.event", "message": "Update id=618064530 is handled. Duration 103 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:03+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg_262182607 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:00:03+0330", "logger": "aiogram.event", "message": "Update id=618064531 is handled. Duration 126 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:06+0330", "logger": "aiogram.event", "message": "Update id=618064532 is handled. Duration 81 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:07+0330", "logger": "aiogram.event", "message": "Update id=618064533 is handled. Duration 351 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:08+0330", "logger": "aiogram.event", "message": "Update id=618064534 is handled. Duration 143 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:13+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:00:13+0330", "logger": "aiogram.event", "message": "Update id=618064535 is handled. Duration 158 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:14+0330", "logger": "aiogram.event", "message": "Update id=618064536 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:16+0330", "logger": "aiogram.event", "message": "Update id=618064537 is handled. Duration 314 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:17+0330", "logger": "aiogram.event", "message": "Update id=618064538 is handled. Duration 165 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:18+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:19+0330", "logger": "aiogram.event", "message": "Update id=618064539 is handled. Duration 1323 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:20+0330", "logger": "aiogram.event", "message": "Update id=618064540 is handled. Duration 59 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:28+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:28+0330", "logger": "aiogram.event", "message": "Update id=618064541 is handled. Duration 148 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:32+0330", "logger": "aiogram.event", "message": "Update id=618064542 is handled. Duration 74 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:33+0330", "logger": "aiogram.event", "message": "Update id=618064543 is handled. Duration 95 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:35+0330", "logger": "aiogram.event", "message": "Update id=618064544 is handled. Duration 303 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:36+0330", "logger": "aiogram.event", "message": "Update id=618064545 is handled. Duration 136 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:37+0330", "logger": "aiogram.event", "message": "Update id=618064546 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:39+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:39+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:39+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:39+0330", "logger": "aiogram.event", "message": "Update id=618064547 is handled. Duration 199 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:42+0330", "logger": "aiogram.event", "message": "Update id=618064548 is handled. Duration 67 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:43+0330", "logger": "aiogram.event", "message": "Update id=618064549 is handled. Duration 105 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:45+0330", "logger": "aiogram.event", "message": "Update id=618064550 is handled. Duration 199 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:46+0330", "logger": "aiogram.event", "message": "Update id=618064551 is handled. Duration 93 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:47+0330", "logger": "aiogram.event", "message": "Update id=618064552 is handled. Duration 82 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:49+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:49+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:49+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:00:49+0330", "logger": "aiogram.event", "message": "Update id=618064553 is handled. Duration 239 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:51+0330", "logger": "aiogram.event", "message": "Update id=618064554 is handled. Duration 85 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:52+0330", "logger": "aiogram.event", "message": "Update id=618064555 is handled. Duration 158 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:58+0330", "logger": "aiogram.event", "message": "Update id=618064556 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:00:59+0330", "logger": "aiogram.event", "message": "Update id=618064557 is handled. Duration 92 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:00+0330", "logger": "aiogram.event", "message": "Update id=618064558 is handled. Duration 104 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:01+0330", "logger": "aiogram.event", "message": "Update id=618064559 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:03+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user/tg8393184061r3l/reset \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:03+0330", "logger": "aiogram.event", "message": "Update id=618064560 is handled. Duration 272 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:15+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user/tg8393184061r3l/reset \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:15+0330", "logger": "aiogram.event", "message": "Update id=618064561 is handled. Duration 155 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:19+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user/tg8393184061r3l/revoke_sub \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:19+0330", "logger": "aiogram.event", "message": "Update id=618064562 is handled. Duration 135 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:29+0330", "logger": "aiogram.event", "message": "Update id=618064563 is handled. Duration 236 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:34+0330", "logger": "aiogram.event", "message": "Update id=618064564 is handled. Duration 60 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:36+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:36+0330", "logger": "aiogram.event", "message": "Update id=618064565 is handled. Duration 154 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:51+0330", "logger": "aiogram.event", "message": "Update id=618064566 is handled. Duration 84 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:52+0330", "logger": "aiogram.event", "message": "Update id=618064567 is handled. Duration 124 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:53+0330", "logger": "aiogram.event", "message": "Update id=618064568 is handled. Duration 89 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:54+0330", "logger": "aiogram.event", "message": "Update id=618064569 is handled. Duration 125 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:55+0330", "logger": "aiogram.event", "message": "Update id=618064570 is handled. Duration 118 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:56+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061b6u \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:01:56+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:56+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:56+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:01:57+0330", "logger": "aiogram.event", "message": "Update id=618064571 is handled. Duration 368 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:01:59+0330", "logger": "aiogram.event", "message": "Update id=618064572 is handled. Duration 81 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:00+0330", "logger": "aiogram.event", "message": "Update id=618064573 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:02+0330", "logger": "aiogram.event", "message": "Update id=618064574 is handled. Duration 97 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:15+0330", "logger": "aiogram.event", "message": "Update id=618064575 is handled. Duration 85 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:17+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:17+0330", "logger": "aiogram.event", "message": "Update id=618064576 is handled. Duration 122 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:18+0330", "logger": "aiogram.event", "message": "Update id=618064577 is handled. Duration 179 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:19+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:20+0330", "logger": "aiogram.event", "message": "Update id=618064578 is handled. Duration 162 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:21+0330", "logger": "aiogram.event", "message": "Update id=618064579 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:25+0330", "logger": "aiogram.event", "message": "Update id=618064580 is handled. Duration 61 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:27+0330", "logger": "aiogram.event", "message": "Update id=618064581 is handled. Duration 62 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:28+0330", "logger": "aiogram.event", "message": "Update id=618064582 is handled. Duration 211 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:29+0330", "logger": "aiogram.event", "message": "Update id=618064583 is handled. Duration 206 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:32+0330", "logger": "aiogram.event", "message": "Update id=618064584 is handled. Duration 134 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:33+0330", "logger": "aiogram.event", "message": "Update id=618064585 is handled. Duration 212 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/inbounds \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: POST https://p.v2pro.store/api/user \"HTTP/1.1 409 Conflict\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061jyx \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061jyx \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:34+0330", "logger": "httpx", "message": "HTTP Request: PUT https://p.v2pro.store/api/user/tg8393184061jyx \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:35+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg8393184061jyx \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:02:35+0330", "logger": "aiogram.event", "message": "Update id=618064586 is handled. Duration 583 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:36+0330", "logger": "aiogram.event", "message": "Update id=618064587 is handled. Duration 163 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:37+0330", "logger": "aiogram.event", "message": "Update id=618064588 is handled. Duration 272 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:38+0330", "logger": "aiogram.event", "message": "Update id=618064589 is handled. Duration 146 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:46+0330", "logger": "aiogram.event", "message": "Update id=618064590 is handled. Duration 68 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:47+0330", "logger": "aiogram.event", "message": "Update id=618064591 is handled. Duration 131 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:02:49+0330", "logger": "aiogram.event", "message": "Update id=618064592 is handled. Duration 247 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:40+0330", "logger": "aiogram.event", "message": "Update id=618064593 is handled. Duration 192 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:41+0330", "logger": "aiogram.event", "message": "Update id=618064594 is handled. Duration 122 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:41+0330", "logger": "aiogram.event", "message": "Update id=618064595 is handled. Duration 118 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:42+0330", "logger": "aiogram.event", "message": "Update id=618064596 is handled. Duration 144 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:43+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061jyx \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:04:43+0330", "logger": "aiogram.event", "message": "Update id=618064597 is handled. Duration 223 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:44+0330", "logger": "aiogram.event", "message": "Update id=618064598 is handled. Duration 157 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:45+0330", "logger": "aiogram.event", "message": "Update id=618064599 is handled. Duration 126 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:46+0330", "logger": "aiogram.event", "message": "Update id=618064600 is handled. Duration 158 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:47+0330", "logger": "aiogram.event", "message": "Update id=618064601 is handled. Duration 172 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:48+0330", "logger": "aiogram.event", "message": "Update id=618064602 is handled. Duration 219 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:49+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061hx4 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:04:49+0330", "logger": "aiogram.event", "message": "Update id=618064603 is handled. Duration 263 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:50+0330", "logger": "aiogram.event", "message": "Update id=618064604 is handled. Duration 342 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:51+0330", "logger": "aiogram.event", "message": "Update id=618064605 is handled. Duration 103 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:52+0330", "logger": "aiogram.event", "message": "Update id=618064606 is handled. Duration 105 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:53+0330", "logger": "aiogram.event", "message": "Update id=618064607 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:54+0330", "logger": "httpx", "message": "HTTP Request: DELETE https://p.v2pro.store/api/user/tg8393184061r3l \"HTTP/1.1 200 OK\""}
{"level": "INFO", "time": "2025-09-07T18:04:54+0330", "logger": "aiogram.event", "message": "Update id=618064608 is handled. Duration 156 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:04:55+0330", "logger": "aiogram.event", "message": "Update id=618064609 is handled. Duration 77 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:00+0330", "logger": "aiogram.event", "message": "Update id=618064610 is handled. Duration 95 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:01+0330", "logger": "aiogram.event", "message": "Update id=618064611 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:03+0330", "logger": "aiogram.event", "message": "Update id=618064612 is handled. Duration 131 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:07+0330", "logger": "aiogram.event", "message": "Update id=618064613 is handled. Duration 54 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:10+0330", "logger": "aiogram.event", "message": "Update id=618064614 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:11+0330", "logger": "aiogram.event", "message": "Update id=618064615 is handled. Duration 160 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:12+0330", "logger": "aiogram.event", "message": "Update id=618064616 is handled. Duration 159 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:21+0330", "logger": "aiogram.event", "message": "Update id=618064617 is handled. Duration 190 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:30+0330", "logger": "aiogram.event", "message": "Update id=618064618 is handled. Duration 303 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:05:32+0330", "logger": "aiogram.event", "message": "Update id=618064619 is handled. Duration 38 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:11+0330", "logger": "aiogram.event", "message": "Update id=618064620 is handled. Duration 132 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:13+0330", "logger": "aiogram.event", "message": "Update id=618064621 is handled. Duration 96 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:14+0330", "logger": "aiogram.event", "message": "Update id=618064622 is handled. Duration 96 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:15+0330", "logger": "aiogram.event", "message": "Update id=618064623 is handled. Duration 239 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:21+0330", "logger": "aiogram.event", "message": "Update id=618064624 is handled. Duration 108 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:28+0330", "logger": "aiogram.event", "message": "Update id=618064625 is handled. Duration 79 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:51+0330", "logger": "aiogram.event", "message": "Update id=618064626 is handled. Duration 101 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:54+0330", "logger": "aiogram.event", "message": "Update id=618064627 is handled. Duration 101 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:06:55+0330", "logger": "aiogram.event", "message": "Update id=618064628 is handled. Duration 156 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:06+0330", "logger": "aiogram.event", "message": "Update id=618064629 is handled. Duration 162 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:07+0330", "logger": "aiogram.event", "message": "Update id=618064630 is handled. Duration 218 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:08+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg_277986867 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:07:08+0330", "logger": "aiogram.event", "message": "Update id=618064631 is handled. Duration 167 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:12+0330", "logger": "aiogram.event", "message": "Update id=618064632 is handled. Duration 63 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:15+0330", "logger": "aiogram.event", "message": "Update id=618064633 is handled. Duration 135 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:18+0330", "logger": "aiogram.event", "message": "Update id=618064634 is handled. Duration 216 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:22+0330", "logger": "app.bot.handlers.wallet", "message": "wallet topup created", "cid": "031d70347716480687d2009c79640469", "topup_id": 6, "user_id": 3, "amount_irr": "100000000", "mime": "photo"}
{"level": "INFO", "time": "2025-09-07T18:07:22+0330", "logger": "aiogram.event", "message": "Update id=618064635 is handled. Duration 141 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:25+0330", "logger": "aiogram.event", "message": "Update id=618064636 is handled. Duration 110 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:25+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_settings_menu: enter", "uid": 262182607}
{"level": "INFO", "time": "2025-09-07T18:07:26+0330", "logger": "aiogram.event", "message": "Update id=618064637 is handled. Duration 168 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:26+0330", "logger": "httpx", "message": "HTTP Request: GET https://p.v2pro.store/api/user/tg_262182607 \"HTTP/1.1 404 Not Found\""}
{"level": "INFO", "time": "2025-09-07T18:07:26+0330", "logger": "aiogram.event", "message": "Update id=618064638 is handled. Duration 418 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:27+0330", "logger": "aiogram.event", "message": "Update id=618064639 is handled. Duration 88 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:30+0330", "logger": "aiogram.event", "message": "Update id=618064640 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:33+0330", "logger": "aiogram.event", "message": "Update id=618064641 is handled. Duration 204 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:37+0330", "logger": "aiogram.event", "message": "Update id=618064642 is handled. Duration 76 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:42+0330", "logger": "aiogram.event", "message": "Update id=618064643 is handled. Duration 58 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:46+0330", "logger": "aiogram.event", "message": "Update id=618064644 is handled. Duration 135 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:47+0330", "logger": "aiogram.event", "message": "Update id=618064645 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:48+0330", "logger": "aiogram.event", "message": "Update id=618064646 is handled. Duration 92 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:51+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_start", "uid": 262182607}
{"level": "INFO", "time": "2025-09-07T18:07:51+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_start.cleanup", "uid": 262182607}
{"level": "INFO", "time": "2025-09-07T18:07:51+0330", "logger": "aiogram.event", "message": "Update id=618064647 is handled. Duration 64 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:52+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_ref", "uid": 262182607, "text": "277986867"}
{"level": "INFO", "time": "2025-09-07T18:07:52+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_ref.stage", "uid": 262182607, "stage": "await_ref"}
{"level": "INFO", "time": "2025-09-07T18:07:52+0330", "logger": "aiogram.event", "message": "Update id=618064648 is handled. Duration 100 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:54+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_unit.enter", "uid": 262182607, "data": "walletadm:add:unit:TMN"}
{"level": "INFO", "time": "2025-09-07T18:07:54+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_unit.choice", "uid": 262182607, "unit": "TMN"}
{"level": "INFO", "time": "2025-09-07T18:07:54+0330", "logger": "aiogram.event", "message": "Update id=618064649 is handled. Duration 172 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:07:57+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_amount.enter", "uid": 262182607, "text": "10000000"}
{"level": "INFO", "time": "2025-09-07T18:07:57+0330", "logger": "app.bot.handlers.wallet", "message": "wallet.admin_manual_add_amount.stage", "uid": 262182607, "stage": "await_amount", "unit": "TMN", "user_id": 3}
{"level": "INFO", "time": "2025-09-07T18:07:57+0330", "logger": "aiogram.event", "message": "Update id=618064650 is handled. Duration 132 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:00+0330", "logger": "aiogram.event", "message": "Update id=618064651 is handled. Duration 89 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:01+0330", "logger": "aiogram.event", "message": "Update id=618064652 is handled. Duration 72 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:02+0330", "logger": "aiogram.event", "message": "Update id=618064653 is handled. Duration 121 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:07+0330", "logger": "aiogram.event", "message": "Update id=618064654 is handled. Duration 70 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:09+0330", "logger": "aiogram.event", "message": "Update id=618064655 is handled. Duration 172 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:11+0330", "logger": "aiogram.event", "message": "Update id=618064656 is handled. Duration 114 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:13+0330", "logger": "aiogram.event", "message": "Update id=618064657 is handled. Duration 94 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:15+0330", "logger": "aiogram.event", "message": "Update id=618064658 is handled. Duration 118 ms by bot id=8458475411"}
{"level": "INFO", "time": "2025-09-07T18:08:16+0330", "logger": "aiogram.event", "message": "Update id=618064659 is handled. Duration 203 ms by bot id=8458475411"}
