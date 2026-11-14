@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    goto :python_missing
)

python -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)"
if errorlevel 1 (
    goto :python_version
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

:python_missing
echo.
echo Python was not found. This app needs Python 3.9 through 3.12.
goto :python_help

:python_version
echo.
echo This app needs Python 3.9 through 3.12. Detected:
python --version

:python_help
echo.
echo Install Python 3.11 (64-bit) from:
echo https://www.python.org/downloads/windows/
echo In the installer, check "Add python.exe to PATH".
choice /C YN /M "Open the official Python download page now"
if errorlevel 2 goto :python_done
start "" "https://www.python.org/downloads/windows/"

:python_done
echo.
echo After installing Python, close this window and run install.bat again.
pause
exit /b 1
