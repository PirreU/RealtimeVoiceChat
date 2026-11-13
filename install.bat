@echo off

:: Set Python path (adjust this if needed)
set PYTHON_EXE=python.exe

setlocal enabledelayedexpansion

:: Set current directory
cd /d %~dp0

echo.
echo Select how to use Real-Time Voice Chat:
echo   S - Set up this computer as a server (installs the AI stack)
echo   C - Connect as a client (no AI stack is installed)
set /p INSTALL_ROLE=Choose S or C:
if /I "%INSTALL_ROLE%"=="C" goto :client
if /I not "%INSTALL_ROLE%"=="S" (
    echo Invalid choice. Run install.bat again and choose S or C.
    exit /b 1
)

echo Starting installation process...

:: Create and activate virtual environment
echo Creating and activating virtual environment...
%PYTHON_EXE% -m venv venv
if errorlevel 1 exit /b 1
call venv\Scripts\activate.bat
if errorlevel 1 exit /b 1

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo Installing torch...
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 exit /b 1
pip install https://raw.githubusercontent.com/KoljaB/RealtimeVoiceChat/main/wheels/deepspeed-0.16.1%%2Bunknown-cp310-cp310-win_amd64.whl
if errorlevel 1 exit /b 1

echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Configuring secure LAN server access...
python setup.py --configure-server
if errorlevel 1 exit /b 1

cmd
exit /b

:client
%PYTHON_EXE% setup.py --client
exit /b %errorlevel%
