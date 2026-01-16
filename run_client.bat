@echo off
REM Run Voice Analyzer client on Windows
REM Project is in WSL, but client runs on Windows Python

set PROJECT_PATH=\\wsl.localhost\Ubuntu\home\amogusik\projects\voice-analyzer
set HOST=localhost
set PORT=9876

echo ================================
echo Voice Analyzer Client
echo ================================
echo Server: %HOST%:%PORT%
echo ================================
echo.

cd /d %PROJECT_PATH%

REM Check if Windows venv exists
if exist "venv_win\Scripts\activate.bat" (
    call venv_win\Scripts\activate.bat
)

python -m client.main --host %HOST% --port %PORT% %*
