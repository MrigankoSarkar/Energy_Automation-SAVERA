# ============================================================================
# EnergyAutomation - Clean Build Script
# ============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " EnergyAutomation - Cleaning Build Artifacts" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot

$DirectoriesToClean = @(
    (Join-Path $ProjectRoot "build"),
    (Join-Path $ProjectRoot "dist"),
    (Join-Path $ProjectRoot ".pytest_cache")
)

foreach ($dir in $DirectoriesToClean) {
    if (Test-Path $dir) {
        Write-Host "Removing: $dir" -ForegroundColor Yellow
        Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Clean __pycache__ recursively
Write-Host "Cleaning __pycache__ folders..." -ForegroundColor Yellow
Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Build artifacts cleaned successfully (preserved source, configs, credentials, user data)." -ForegroundColor Green
