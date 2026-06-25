@echo off
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=py -3"
)

echo Starting L10 Web UI at http://127.0.0.1:8765/
echo Backend: sdk (use dashboard only when dashboard.exe is running)

if exist "config\l10_left.yaml" (
    %PYTHON% -m l10_hand_control.web_server --backend sdk --config config\l10_left.yaml %*
) else (
    %PYTHON% -m l10_hand_control.web_server --backend sdk %*
)
