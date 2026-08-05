@echo off
cd /d "%~dp0"
title Snore Social - Local

echo.
echo    === Snore Social - Local Start ===
echo.

:: 1. Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

:: 2. Create venv
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment ready

:: 3. Install dependencies
echo [INFO] Installing dependencies (this may take a while)...
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency install failed. Check your network.
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: 4. Setup .env
if not exist "backend\.env" (
    copy backend\.env.example backend\.env >nul
    echo [INFO] Created backend\.env from template
)

:: 5. Use SQLite for local dev (no PostgreSQL needed)
set DATABASE_URL=sqlite:///./backend/snore.db

:: 6. Start server
echo.
echo    Starting server at http://localhost:8000
echo    Press Ctrl+C to stop
echo.
start "" http://localhost:8000

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
