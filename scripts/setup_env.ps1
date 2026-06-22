$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    py -3.12 -m venv (Join-Path $Root ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "$Root[test]"

Write-Host "Environment ready."
Write-Host "Python: $VenvPython"
Write-Host "Run tests: .\.venv\Scripts\python.exe -m pytest -q"
