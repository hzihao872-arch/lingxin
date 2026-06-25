# Launch the L10 joint control web UI.
# If PowerShell blocks this script, use:  scripts\run_web_ui.cmd
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (Test-Path "$Root\.venv\Scripts\python.exe") {
    $Python = "$Root\.venv\Scripts\python.exe"
} else {
    $Python = "py"
    $PyArgs = @("-3")
}

$Config = "$Root\config\l10_left.yaml"
$ModuleArgs = @("-m", "l10_hand_control.web_server", "--host", "127.0.0.1", "--port", "8765")

if (Test-Path $Config) {
    $ModuleArgs += @("--config", $Config)
}

Write-Host "Starting L10 Web UI at http://127.0.0.1:8765/"
if ($PyArgs) {
    & $Python @PyArgs @ModuleArgs
} else {
    & $Python @ModuleArgs
}
