@echo off
setlocal EnableDelayedExpansion

:: VolatilityHunter standalone Windows deploy script
:: -------------------------------------------------
:: Run this batch file from the VolatilityHunter repo root to package, upload,
:: and restart the VolatilityHunter container on the VPS.
::
:: Required environment:
::   SERVER        - VPS SSH target, e.g. root@207.154.218.23
::   SSH_KEY_PATH  - Absolute path to your SSH private key for the VPS
::
:: Accepted ways to pass the key:
::   1. As the first argument: .\deploy_volatilityhunter.bat C:\Users\Yaniv\.ssh\id_ed25519
::   2. As the SSH_KEY_PATH environment variable
::   3. As the legacy SSH_KEY environment variable
::   4. Defaults to C:\Users\<username>\.ssh\id_ed25519 if nothing is provided
::
:: Example usage:
::   .\deploy_volatilityhunter.bat C:\Users\Yaniv\.ssh\id_ed25519

set "SERVER=root@207.154.218.23"
set "PROJECT=%~dp0"
set "ARCHIVE=%TEMP%\volatilityhunter-deploy-%RANDOM%.tar.gz"

:: 1. Resolve SSH key path: argument > SSH_KEY_PATH > SSH_KEY > default
if not "%~1"=="" (
    set "SSH_KEY_PATH=%~1"
) else if not defined SSH_KEY_PATH (
    if defined SSH_KEY (
        set "SSH_KEY_PATH=%SSH_KEY%"
    ) else (
        set "SSH_KEY_PATH=C:\Users\%USERNAME%\.ssh\id_ed25519"
    )
)

echo [INFO] Using SSH key: %SSH_KEY_PATH%
if not exist "%SSH_KEY_PATH%" (
    echo [ERROR] SSH key not found: %SSH_KEY_PATH%
    echo [INFO] Pass the key as the first argument, or set SSH_KEY_PATH / SSH_KEY.
    pause
    exit /b 1
)
set "SSH_OPTS=-i "%SSH_KEY_PATH%""

:: 2. Ensure we are in the VolatilityHunter repo
if not exist "%PROJECT%\scripts\daily_trading_loop.py" (
    echo [ERROR] scripts\daily_trading_loop.py not found in %PROJECT%
    pause
    exit /b 1
)

:: 3. Quick syntax validation before packaging
echo [INFO] Running py_compile sanity check...
python -m py_compile "%PROJECT%\scripts\daily_trading_loop.py" "%PROJECT%\scripts\update_data.py" "%PROJECT%\scripts\functional_health_check.py" "%PROJECT%\scripts\live_reconciliation.py" "%PROJECT%\src\brokerage_interface.py" "%PROJECT%\src\email_notifier.py" "%PROJECT%\src\telegram_notifier.py" "%PROJECT%\src\strategy_engine.py"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python syntax check failed. Fix before deploying.
    pause
    exit /b %ERRORLEVEL%
)

:: 4. Confirm SSH connectivity
echo [INFO] Testing SSH connectivity to %SERVER%...
ssh %SSH_OPTS% %SERVER% "echo [OK] SSH connectivity verified" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Cannot SSH to %SERVER% with key %SSH_KEY_PATH%
    echo [INFO] Check that the key is authorized on the VPS and the SSH service is reachable.
    pause
    exit /b 1
)

:: 5. Upload .env (always overwrite with local source of truth)
echo [INFO] Uploading VolatilityHunter .env...
scp %SSH_OPTS% "%PROJECT%\.env" %SERVER%:/root/volatilityhunter/.env
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to upload VolatilityHunter .env
    pause
    exit /b %ERRORLEVEL%
)

:: 6. Seed market data if not present on VPS
echo [INFO] Checking market data seed on the VPS...
ssh %SSH_OPTS% %SERVER% "test -f /root/volatilityhunter/data/portfolio.json" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] No VolatilityHunter state found on VPS. Building data seed archive locally...
    set "DATA_ARCHIVE=%TEMP%\volatilityhunter-data-%RANDOM%.tar.gz"
    tar -czf "!DATA_ARCHIVE!" -C "%PROJECT:~0,-1%" data\raw 2>nul || echo [INFO] data\raw not present locally, skipping seed.
    if exist "!DATA_ARCHIVE!" (
        echo [INFO] Uploading market data seed. This may take several minutes...
        scp %SSH_OPTS% "!DATA_ARCHIVE!" %SERVER%:/root/volatilityhunter-data.tar.gz
        if !ERRORLEVEL! NEQ 0 (
            echo [ERROR] Failed to upload data/raw seed
            pause
            exit /b !ERRORLEVEL!
        )
        echo [INFO] Extracting market data seed on VPS...
        ssh %SSH_OPTS% %SERVER% "mkdir -p /root/volatilityhunter && cd /root/volatilityhunter && tar -xzf /root/volatilityhunter-data.tar.gz && rm -f /root/volatilityhunter-data.tar.gz"
        if !ERRORLEVEL! NEQ 0 (
            echo [ERROR] Failed to extract data/raw seed on VPS
            pause
            exit /b !ERRORLEVEL!
        )
    )
)

:: 7. Build archive excluding local state and secrets
tar -czf "%ARCHIVE%" -C "%PROJECT:~0,-1%"^
 --exclude=".git"^
 --exclude="data"^
 --exclude="logs"^
 --exclude="reports"^
 --exclude="__pycache__"^
 --exclude=".pytest_cache"^
 --exclude="venv"^
 --exclude=".venv"^
 --exclude="*.db"^
 --exclude="*.sqlite3"^
 --exclude=".env"^
 --exclude=".env.*"^
 .

:: 8. Upload
echo [INFO] Uploading VolatilityHunter archive to %SERVER%...
scp %SSH_OPTS% "%ARCHIVE%" %SERVER%:/root/volatilityhunter-deploy.tar.gz
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] SCP failed
    pause
    exit /b %ERRORLEVEL%
)

:: 9. Deploy on the VPS
echo [INFO] Deploying VolatilityHunter on %SERVER%...
ssh %SSH_OPTS% %SERVER% "mkdir -p /root/volatilityhunter && cd /root/volatilityhunter && rm -rf src scripts config TWSibgateway tickers.txt *.py *.toml *.txt *.sh *.yml *.md Dockerfile requirements-docker.txt && tar -xzf /root/volatilityhunter-deploy.tar.gz && rm -f /root/volatilityhunter-deploy.tar.gz && docker network inspect family-agents-net >/dev/null 2>&1 || docker network create family-agents-net && docker compose -f docker-compose.yml -p volatilityhunter down && docker compose -f docker-compose.yml -p volatilityhunter up -d --build && docker compose -p volatilityhunter ps"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Remote deployment failed
    pause
    exit /b %ERRORLEVEL%
)

echo [OK] VolatilityHunter deployed successfully.
pause
