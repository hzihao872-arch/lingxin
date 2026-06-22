$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root "vendor"
$SdkDir = Join-Path $Vendor "linkerhand-python-sdk"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $VenvPython)) {
    & (Join-Path $PSScriptRoot "setup_env.ps1")
}

New-Item -ItemType Directory -Force $Vendor | Out-Null

if (Test-Path $SdkDir) {
    Invoke-Checked { git -C $SdkDir pull --ff-only } "git pull"
} else {
    try {
        Invoke-Checked { git clone https://github.com/linker-bot/linkerhand-python-sdk.git $SdkDir } "git clone"
    } catch {
        if (Test-Path $SdkDir) {
            Remove-Item -LiteralPath $SdkDir -Recurse -Force
        }
        throw
    }
}

Invoke-Checked { & $VenvPython -m pip install python-can python-can-candle numpy PyYAML requests } "pip install SDK dependencies"

Write-Host "Official SDK checkout ready: $SdkDir"
Write-Host "Use with: .\.venv\Scripts\python.exe -m l10_hand_control --backend sdk --sdk-path `"$SdkDir`" list-devices"
