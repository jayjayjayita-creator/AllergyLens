@echo off
title AllergyLens Local Server
cd /d "%~dp0"

echo.
echo  ==========================================
echo   AllergyLens - Food Allergy Checker
echo   Local Setup and Launch
echo  ==========================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Download from https://www.python.org/downloads/
    echo         Make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found.

:: 2. Check for Tesseract (OCR support)
set "TESS_CMD=tesseract"
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set "TESS_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"
        echo [OK] Tesseract found.
    ) else (
        echo [WARN] Tesseract not found. Image OCR will not work.
        echo        Manual text entry will still work fine.
        echo        Install from: https://github.com/UB-Mannheim/tesseract/wiki
        echo.
    )
) else (
    echo [OK] Tesseract found.
)

:: 3. Create virtual environment if it doesn't exist
if not exist "venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment ready.
)

:: 4. Install/update dependencies
echo [SETUP] Installing dependencies (this may take a minute on first run)...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dependency install failed.
    echo         If you see a Pillow or zlib error, your Python version may be too new.
    echo         Recommended: Python 3.11 or 3.12 from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencies ready.

:: 5. Create folders
if not exist "data"    mkdir data
if not exist "uploads" mkdir uploads

:: 6. Set environment variables
set "FLASK_ENV=development"
set "DATABASE_PATH=%~dp0data\allergylens.db"
set "UPLOAD_FOLDER=%~dp0uploads"
set "TESSERACT_CMD=%TESS_CMD%"
set "SECRET_KEY=local-dev-secret"

:: 7. Open browser after a short delay (runs in background)
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5000"

:: 8. Start Flask
echo.
echo  ==========================================
echo   AllergyLens is starting...
echo   Browser will open at http://localhost:5000
echo   Press Ctrl+C to stop.
echo  ==========================================
echo.

venv\Scripts\python.exe app.py

pause
