@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Root path (change if needed)
set "ROOT=C:\Users\Behnam\Documents\GitHub\MarzbanSudo"

echo Creating directories...

for %%D in (
"docker"
"scripts"
"app"
"app\utils"
"app\db"
"app\db\crud"
"app\db\migrations"
"app\db\migrations\versions"
"app\marzban"
"app\services"
"app\payment"
"app\payment\providers"
"app\bot"
"app\bot\middlewares"
"app\bot\filters"
"app\bot\keyboards"
"app\bot\callbacks"
"app\bot\handlers"
"tests"
) do (
  if not exist "%ROOT%\%%~D" (
    mkdir "%ROOT%\%%~D"
    echo [+] Dir: %ROOT%\%%~D
  ) else (
    echo [=] Dir exists: %ROOT%\%%~D
  )
)

echo Creating files...

call :touch "%ROOT%\README.md"
call :touch "%ROOT%\.env.example"
call :touch "%ROOT%\requirements.txt"
call :touch "%ROOT%\alembic.ini"
call :touch "%ROOT%\docker-compose.yml"

call :touch "%ROOT%\docker\Dockerfile"
call :touch "%ROOT%\docker\bot-entrypoint.sh"

call :touch "%ROOT%\scripts\setup.sh"
call :touch "%ROOT%\scripts\run_dev.sh"
call :touch "%ROOT%\scripts\alembic.sh"

call :touch "%ROOT%\app\__init__.py"
call :touch "%ROOT%\app\main.py"
call :touch "%ROOT%\app\bootstrap.py"
call :touch "%ROOT%\app\config.py"
call :touch "%ROOT%\app\logging_config.py"

call :touch "%ROOT%\app\utils\__init__.py"
call :touch "%ROOT%\app\utils\time.py"
call :touch "%ROOT%\app\utils\money.py"
call :touch "%ROOT%\app\utils\username.py"
call :touch "%ROOT%\app\utils\crypto.py"

call :touch "%ROOT%\app\db\__init__.py"
call :touch "%ROOT%\app\db\base.py"
call :touch "%ROOT%\app\db\models.py"

call :touch "%ROOT%\app\db\crud\__init__.py"
call :touch "%ROOT%\app\db\crud\users.py"
call :touch "%ROOT%\app\db\crud\plans.py"
call :touch "%ROOT%\app\db\crud\orders.py"
call :touch "%ROOT%\app\db\crud\transactions.py"

call :touch "%ROOT%\app\db\migrations\env.py"
call :touch "%ROOT%\app\db\migrations\script.py.mako"

call :touch "%ROOT%\app\marzban\__init__.py"
call :touch "%ROOT%\app\marzban\schemas.py"
call :touch "%ROOT%\app\marzban\client.py"

call :touch "%ROOT%\app\services\__init__.py"
call :touch "%ROOT%\app\services\provisioning.py"
call :touch "%ROOT%\app\services\billing.py"
call :touch "%ROOT%\app\services\notifications.py"
call :touch "%ROOT%\app\services\scheduler.py"
call :touch "%ROOT%\app\services\security.py"

call :touch "%ROOT%\app\payment\__init__.py"
call :touch "%ROOT%\app\payment\manual_transfer.py"
call :touch "%ROOT%\app\payment\providers\__init__.py"
call :touch "%ROOT%\app\payment\providers\zarinpal.py"
call :touch "%ROOT%\app\payment\providers\idpay.py"

call :touch "%ROOT%\app\bot\__init__.py"
call :touch "%ROOT%\app\bot\middlewares\__init__.py"
call :touch "%ROOT%\app\bot\middlewares\auth.py"
call :touch "%ROOT%\app\bot\middlewares\throttling.py"
call :touch "%ROOT%\app\bot\filters\__init__.py"
call :touch "%ROOT%\app\bot\filters\admin_filter.py"
call :touch "%ROOT%\app\bot\keyboards\__init__.py"
call :touch "%ROOT%\app\bot\keyboards\common.py"
call :touch "%ROOT%\app\bot\keyboards\admin.py"
call :touch "%ROOT%\app\bot\callbacks\__init__.py"
call :touch "%ROOT%\app\bot\callbacks\purchase.py"
call :touch "%ROOT%\app\bot\handlers\__init__.py"
call :touch "%ROOT%\app\bot\handlers\start.py"
call :touch "%ROOT%\app\bot\handlers\plans.py"
call :touch "%ROOT%\app\bot\handlers\orders.py"
call :touch "%ROOT%\app\bot\handlers\account.py"
call :touch "%ROOT%\app\bot\handlers\admin.py"

call :touch "%ROOT%\tests\__init__.py"
call :touch "%ROOT%\tests\test_smoke.py"

echo Done.
exit /b 0

:touch
REM Creates an empty file if not exists
set "TARGET=%~1"
if not exist "%TARGET%" (
  type nul > "%TARGET%"
  echo [+] File: %TARGET%
) else (
  echo [=] File exists: %TARGET%
)
exit /b 0
