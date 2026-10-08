# ============================================================================
# EnergyAutomation - Production Windows Distribution and Installer Build
# ============================================================================
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
Set-Location -Path $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ENERGYAUTOMATION - WINDOWS 11 PRODUCTION BUILD PIPELINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Validate Python Environment
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "Python executable not found in .venv or PATH."
        exit 1
    }
}

Write-Host "[1/8] Verifying Python runtime..." -ForegroundColor Green
& $PythonExe --version

# 2. Extract Version from app/version.py
$VersionScript = "from app.version import APP_VERSION; print(APP_VERSION)"
$AppVersion = (& $PythonExe -c $VersionScript).Trim()
Write-Host "      Detected Application Version: $AppVersion" -ForegroundColor Yellow

# 3. Clean Previous Builds
Write-Host "[2/8] Cleaning previous build artifacts..." -ForegroundColor Green
& "$PSScriptRoot\clean_build.ps1"

# 4. Bytecode Verification (compileall)
Write-Host "[3/8] Checking syntax and byte-compiling codebase..." -ForegroundColor Green
& $PythonExe -m compileall -q app ui main.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "compileall failed. Please fix syntax errors."
    exit 1
}

# 5. Automated Tests
if (-not $SkipTests) {
    Write-Host "[4/8] Running automated test suite..." -ForegroundColor Green
    & $PythonExe -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Automated test suite failed. Production build aborted."
        exit 1
    }
    Write-Host "      Test suite passed." -ForegroundColor Green
} else {
    Write-Host "[4/8] Skipping automated tests as requested." -ForegroundColor Yellow
}

# 6. PyInstaller Build
Write-Host "[5/8] Compiling standalone Windows application via PyInstaller..." -ForegroundColor Green
& $PythonExe -m PyInstaller --noconfirm --clean EnergyAutomation.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller compilation failed."
    exit 1
}

$DistDir = Join-Path $ProjectRoot "dist\EnergyAutomation"
$MainExe = Join-Path $DistDir "EnergyAutomation.exe"

if (-not (Test-Path $MainExe)) {
    Write-Error "Expected executable '$MainExe' was not produced."
    exit 1
}
Write-Host "      PyInstaller standalone distribution produced successfully." -ForegroundColor Green

# 7. Package Portable ZIP Release Artifact
Write-Host "[6/8] Creating standalone portable distribution..." -ForegroundColor Green
$ReleaseDir = Join-Path $ProjectRoot "release"
if (-not (Test-Path $ReleaseDir)) {
    New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
}

$Win64DistDir = Join-Path $ReleaseDir "EnergyAutomation-$AppVersion-win64"
if (Test-Path $Win64DistDir) {
    Remove-Item -Path $Win64DistDir -Recurse -Force
}
Copy-Item -Path $DistDir -Destination $Win64DistDir -Recurse

$ZipBase = Join-Path $ReleaseDir "EnergyAutomation-$AppVersion-win64"
$ZipFile = "$ZipBase.zip"
if (Test-Path $ZipFile) {
    Remove-Item -Path $ZipFile -Force
}
Start-Sleep -Milliseconds 500
& $PythonExe -c "import shutil; shutil.make_archive(r'$ZipBase', 'zip', r'$Win64DistDir')"
Write-Host "      Portable package created: $ZipFile" -ForegroundColor Green

# 8. Compile Inno Setup Installer
if (-not $SkipInstaller) {
    Write-Host "[7/8] Locating Inno Setup compiler (ISCC.exe)..." -ForegroundColor Green
    $IsccCandidates = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source,
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $IsccPath = $null
    foreach ($cand in $IsccCandidates) {
        if ($cand -and (Test-Path $cand)) {
            $IsccPath = $cand
            break
        }
    }

    if (-not $IsccPath) {
        Write-Warning "Inno Setup compiler (ISCC.exe) was not found. Skipping installer generation."
    } else {
        Write-Host "      Using ISCC compiler: $IsccPath" -ForegroundColor Yellow
        $IssFile = Join-Path $ProjectRoot "installer\EnergyAutomation.iss"
        & $IsccPath "/Q" $IssFile
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Inno Setup compilation failed."
            exit 1
        }

        $SetupExe = Join-Path $ReleaseDir "EnergyAutomation-$AppVersion-Setup.exe"
        if (-not (Test-Path $SetupExe)) {
            Write-Error "Installer executable '$SetupExe' was not generated."
            exit 1
        }
        Write-Host "      Installer created successfully: $SetupExe" -ForegroundColor Green
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " BUILD COMPLETE! Release Artifacts:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Get-ChildItem -Path $ReleaseDir | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
