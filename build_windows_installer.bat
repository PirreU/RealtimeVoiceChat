@echo off
setlocal
cd /d "%~dp0"

set "BUILD_ENV=%TEMP%\rvchat-installer-build"
if not exist "%BUILD_ENV%\Scripts\python.exe" (
    python -m venv "%BUILD_ENV%"
    if errorlevel 1 exit /b 1
)

"%BUILD_ENV%\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
    echo The installer builder requires Python 3.11.
    exit /b 1
)

"%BUILD_ENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%BUILD_ENV%\Scripts\python.exe" -m pip install -r requirements-windows-installer-build.txt
if errorlevel 1 exit /b 1

"%BUILD_ENV%\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --clean --onefile --windowed ^
    --name RealTimeVoiceChatInstaller ^
    --distpath "%~dp0dist" ^
    --workpath "%TEMP%\rvchat-installer-pyinstaller-work" ^
    --specpath "%TEMP%\rvchat-installer-pyinstaller-spec" ^
    --icon "%~dp0code\static\favicon.ico" ^
    --add-data "%~dp0code;code" ^
    --add-data "%~dp0requirements.txt;." ^
    --add-data "%~dp0setup.py;." ^
    --add-data "%BUILD_ENV%\Scripts\uv.exe;." ^
    "%~dp0windows_gui_installer.py"
if errorlevel 1 exit /b 1

echo.
echo Installer created: %~dp0dist\RealTimeVoiceChatInstaller.exe
