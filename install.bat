@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_COMMAND="
where py >nul 2>nul
if errorlevel 1 goto :check_python_command
py -3.12 -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=py -3.12"
if defined PYTHON_COMMAND goto :python_ready
py -3.11 -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=py -3.11"
if defined PYTHON_COMMAND goto :python_ready
py -3.10 -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=py -3.10"
if defined PYTHON_COMMAND goto :python_ready
py -3.9 -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=py -3.9"
if defined PYTHON_COMMAND goto :python_ready

:check_python_command
if not defined PYTHON_COMMAND (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_COMMAND=python"
    )
)
if not defined PYTHON_COMMAND goto :python_unavailable
goto :python_ready

:python_ready
echo Using %PYTHON_COMMAND%
%PYTHON_COMMAND% --version
if not exist "venv\Scripts\python.exe" (
    echo Creating a private Python environment...
    %PYTHON_COMMAND% -m venv venv
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

:python_unavailable
where py >nul 2>nul
if not errorlevel 1 (
    echo No supported Python was found. Python 3.9 through 3.12 is required.
    choice /C YN /M "Install Python 3.12 with the Python install manager now"
    if errorlevel 2 goto :python_help
    py install 3.12
    if errorlevel 1 goto :python_help
    py -3.12 -c "import sys; raise SystemExit(0 if (3, 9) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
    if errorlevel 1 goto :python_help
    set "PYTHON_COMMAND=py -3.12"
    goto :python_ready
)

where python >nul 2>nul
if errorlevel 1 goto :python_missing
goto :python_version

:python_missing
echo.
echo Python was not found.
goto :python_help

:python_version
echo.
echo This app needs Python 3.9 through 3.12. Detected:
python --version

:python_help
echo.
echo Recommended: install Python 3.12 with the Python install manager:
echo     py install 3.12
echo The last Python 3.12 release with a Windows installer is 3.12.10 (64-bit):
echo https://www.python.org/downloads/release/python-31210/
echo Choose "Windows installer (64-bit)", not the embeddable package.
echo In the installer, check "Add python.exe to PATH".
choice /C YN /M "Open the official Python 3.12 download page now"
if errorlevel 2 goto :python_done
start "" "https://www.python.org/downloads/release/python-31210/"

:python_done
echo.
echo After installing Python 3.12, close this window and run install.bat again.
pause
exit /b 1
