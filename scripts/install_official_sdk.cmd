@echo off
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=py -3"
)

if not exist "vendor" mkdir vendor

if exist "vendor\linkerhand-python-sdk\.git" (
    echo Updating SDK...
    git -C vendor\linkerhand-python-sdk pull --ff-only
) else (
    echo Cloning official LinkerHand SDK...
    git clone https://github.com/linker-bot/linkerhand-python-sdk.git vendor\linkerhand-python-sdk
    if errorlevel 1 exit /b 1
)

%PYTHON% -m pip install -e ".[sdk]" -q
echo.
echo SDK ready: vendor\linkerhand-python-sdk
echo Start web UI with: scripts\run_web_ui.cmd
