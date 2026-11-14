@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.9 through 3.12, then run this installer again.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)"
if errorlevel 1 (
    echo This app requires Python 3.9 through 3.12.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating a private Python environment...
    python -m venv venv
    if errorlevel 1 goto :failed
)

echo Installing application dependencies...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Installation complete. Run start_venv.bat, then enter: python code\server.py
pause
exit /b 0

:failed
echo.
echo Installation failed. Review the error above and try again.
pause
exit /b 1
