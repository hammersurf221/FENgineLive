@echo off
chcp 65001 >nul
echo =====================================
echo   CCN Chess Helper - Setup Script
echo =====================================
echo.

REM Step 0: Check Python version
echo Checking Python version...
timeout /t 1 >nul
python --version > tmp_version.txt 2>&1
findstr /R "^Python 3\.10" tmp_version.txt >nul
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python 3.10 is required.
    echo Please install it from:
    echo   https://www.python.org/downloads/release/python-3100/
    del tmp_version.txt
    pause
    exit /b
)
del tmp_version.txt
echo [OK] Python 3.10 is installed.
timeout /t 2 >nul

REM Step 1: Install required packages
echo.
echo Installing required Python packages...
timeout /t 1 >nul
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install required packages.
    echo Make sure pip is installed and your internet connection is working.
    pause
    exit /b
)
timeout /t 1 >nul

REM Step 2: Check for Stockfish
echo.
echo Verifying Stockfish installation...
timeout /t 1 >nul
IF NOT EXIST stockfish.exe (
    echo [ERROR] Stockfish is missing!
    echo Please download it from https://stockfishchess.org/download/
    echo Rename it to 'stockfish.exe' and place it in this folder.
    pause
    exit /b
)
echo [OK] Stockfish is present.
timeout /t 2 >nul

echo.
echo [DONE] Setup complete.
timeout /t 1 >nul

REM Step 3: Launch the app
echo Launching the app...
timeout /t 1 >nul
python ccn_helper/app.py
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to launch the app.
    pause
    exit /b
)

pause
