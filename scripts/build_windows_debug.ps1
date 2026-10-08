# ============================================================================
# EnergyAutomation - Debug Windows Build Script (Console Enabled)
# ============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
Set-Location -Path $ProjectRoot

Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " ENERGYAUTOMATION - WINDOWS 11 DEBUG BUILD (CONSOLE ENABLED)" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}

Write-Host "Compiling debug standalone build..." -ForegroundColor Green
& $PythonExe -m PyInstaller --noconfirm EnergyAutomation_debug.spec

$DebugExe = Join-Path $ProjectRoot "dist\EnergyAutomation_Debug\EnergyAutomation_Debug.exe"
if (Test-Path $DebugExe) {
    Write-Host "Debug build succeeded: $DebugExe" -ForegroundColor Green
    Write-Host "Run this executable from PowerShell or Command Prompt to view diagnostic output." -ForegroundColor Cyan
} else {
    Write-Error "Debug executable was not produced."
}
