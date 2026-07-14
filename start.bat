@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=%~dp0venv\Scripts\python.exe"
set "REQ=%~dp0requirements.txt"
set "MIRROR=-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn"

echo.
echo Project folder:
echo   %~dp0
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Install Python 3 and enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "%PY%" (
    echo Creating venv...
    python -m venv "%~dp0venv"
    if errorlevel 1 (
        echo [ERROR] Cannot create venv.
        pause
        exit /b 1
    )
)

"%PY%" -c "import uvicorn" 1>nul 2>nul
if errorlevel 1 (
    echo Installing packages into this project venv...
    "%PY%" -m pip install --upgrade pip %MIRROR%
    "%PY%" -m pip install -r "%REQ%" %MIRROR% --default-timeout=180
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check internet/VPN and try again.
        pause
        exit /b 1
    )
)

"%PY%" -c "import uvicorn" 1>nul 2>nul
if errorlevel 1 (
    echo [ERROR] uvicorn still missing after install.
    pause
    exit /b 1
)

netstat -ano | findstr ":8000" | findstr "LISTENING" 1>nul 2>nul
if not errorlevel 1 (
    echo [ERROR] Port 8000 is already in use.
    echo Close the other server window, then run start.bat again.
    pause
    exit /b 1
)

echo.
echo   Site:    http://127.0.0.1:8000/ui/
echo   Swagger: http://127.0.0.1:8000/docs
echo   Stop:    Ctrl+C
echo.

"%PY%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

echo.
pause
