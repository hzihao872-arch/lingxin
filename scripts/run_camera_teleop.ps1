# Run L10 camera teleop with the Windows Python launcher (`py`).
# Usage:
#   .\scripts\run_camera_teleop.ps1
#   .\scripts\run_camera_teleop.ps1 -DryRun
#   .\scripts\run_camera_teleop.ps1 -Backend sdk

param(
    [switch]$DryRun,
    [ValidateSet("dashboard", "sdk")]
    [string]$Backend = "dashboard",
    [string]$SdkPath = "vendor\linkerhand-python-sdk"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python launcher 'py' was not found. Install Python 3.10+ from https://www.python.org/downloads/"
}

Write-Host "Using Python:" -NoNewline
py --version

py -m pip install -e ".[sdk]" -q

$argsList = @("examples/l10_camera_teleop.py", "--backend", $Backend)
if ($DryRun) {
    $argsList += "--dry-run"
}
if ($Backend -eq "sdk") {
    $argsList += @("--sdk-path", $SdkPath)
}

py @argsList
