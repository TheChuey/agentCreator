# Venv setup + activation for the whole agentCreator workspace.
# Usage:  .\scripts\venv.ps1            (activate; create + install if missing)
#         .\scripts\venv.ps1 -Recreate  (wipe and rebuild the venv)
#
# NOTE the folder is named .venv (dot-prefixed), so the manual equivalent is:
#     .\.venv\Scripts\Activate.ps1
# or, for one-off commands:
#     .\.venv\Scripts\python.exe -m pip install ...
param([switch]$Recreate)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if ($Recreate) {
    if (Test-Path (Join-Path $root ".venv")) {
        Write-Host "Removing old venv..." -ForegroundColor Yellow
        Remove-Item -LiteralPath (Join-Path $root ".venv") -Recurse -Force
    }
}

if (-not (Test-Path $python)) {
    Write-Host "Creating venv at $root\.venv ..." -ForegroundColor Cyan
    python -m venv (Join-Path $root ".venv")
    if (-not $?) { throw "Failed to create the virtual environment." }
}

if ($Recreate -or -not (Test-Path (Join-Path $root ".venv\Lib\site-packages\httpx"))) {
    Write-Host "Installing Project Manager + headless engine dependencies..." -ForegroundColor Cyan
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $root "project_manager\requirements.txt")
    & $python -m pip install "httpx>=0.27" "websockets>=13" "fastapi>=0.115" "pydantic>=2" "ollama>=0.3"
}

# Activate with ExecutionPolicy bypass so Activate.ps1 is never blocked.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& (Join-Path $root ".venv\Scripts\Activate.ps1")

Write-Host ""
Write-Host "Venv active. Python: $($python)" -ForegroundColor Green