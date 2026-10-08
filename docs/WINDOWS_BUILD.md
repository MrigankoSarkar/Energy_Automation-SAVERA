# EnergyAutomation — Windows 11 Build & Distribution Guide

This document describes the reproducible build engineering pipeline for **EnergyAutomation**, turning Python source code into a standalone, enterprise-ready Windows 11 desktop application and installer.

---

## 1. Prerequisites & Toolchain

| Tool / Dependency | Tested Version | Purpose |
| :--- | :--- | :--- |
| **Windows OS** | Windows 11 Pro / Enterprise x64 | Target platform |
| **Python** | 3.14.7 x64 | Language runtime |
| **PyInstaller** | 6.22.3 | Standalone PE executable bundler |
| **Inno Setup** | 6.7.3 (`ISCC.exe`) | Professional Windows installer compiler |
| **PySide6** | 6.11.2 | Qt GUI framework |
| **QFluentWidgets** | 1.11.3 | Windows 11 Fluent UI components |

---

## 2. Directory Architecture

```text
EnergyAutomation/
├── assets/                     # Application icons and branding (read-only)
│   ├── app.ico
│   ├── savera-logo.jpg
│   └── favicon.jpg
├── config/                     # Application configurations & templates
│   ├── settings.template.json  # Clean distribution template (no secrets)
│   └── services.json
├── templates/                  # Seed resources
│   └── Sample_BI_Analysis_Report.xlsx
├── installer/                  # Distribution & packaging resources
│   ├── EnergyAutomation.iss    # Inno Setup production script
│   └── file_version_info.txt   # Windows PE metadata (Company, Product, Version)
├── scripts/                    # Automation build scripts
│   ├── build_windows.ps1       # One-click production release pipeline
│   ├── build_windows.bat       # CMD wrapper for PowerShell pipeline
│   ├── build_windows_debug.ps1 # Diagnostic debug build (console enabled)
│   └── clean_build.ps1         # Safe artifact cleaning
├── dist/                       # PyInstaller outputs (generated)
│   └── EnergyAutomation/
│       └── EnergyAutomation.exe
└── release/                    # Final commercial deliverables (generated)
    ├── EnergyAutomation-2.0.0-win64.zip
    └── EnergyAutomation-2.0.0-Setup.exe
```

---

## 3. Production Build Pipeline

To trigger the complete build pipeline (bytecode validation, unit testing, PyInstaller packaging, ZIP creation, and Inno Setup compilation):

```powershell
# Open PowerShell in repository root
.\scripts\build_windows.ps1
```

Or using the Command Prompt wrapper:

```cmd
scripts\build_windows.bat
```

### Pipeline Execution Steps:
1. **Python Runtime Validation**: Verifies Python 3.14+ in virtual environment.
2. **Version Synchronization**: Reads version dynamically from `app/version.py`.
3. **Clean Artifacts**: Purges previous `build/`, `dist/`, and `__pycache__` directories while safely preserving all user configurations, databases, and credentials.
4. **Bytecode Verification**: Runs `python -m compileall` across all modules.
5. **Test Suite**: Executes `pytest -q` to guarantee 100% test pass before packaging.
6. **PyInstaller Compilation**: Builds `dist/EnergyAutomation/EnergyAutomation.exe` with `EnergyAutomation.spec` (windowed, no console, embedded icon, embedded version resource).
7. **Portable Release**: Generates `release/EnergyAutomation-<version>-win64.zip`.
8. **Inno Setup Compilation**: Compiles `release/EnergyAutomation-<version>-Setup.exe`.

---

## 4. Debug Build (Console Enabled)

For troubleshooting startup issues or viewing real-time background logs directly in a terminal:

```powershell
.\scripts\build_windows_debug.ps1
```

This generates `dist/EnergyAutomation_Debug/EnergyAutomation_Debug.exe` with an attached console window.

---

## 5. Security & Secret Safeguards

The build pipeline enforces strict data isolation:
- **No API Keys**: Production templates contain empty API keys (`""`).
- **No OAuth Tokens**: `credentials/credentials.json` and `credentials/token.json` are excluded from the PyInstaller `.spec` and Inno Setup `.iss`.
- **No Development Data**: `data/automation.db` and debug logs are excluded.

---

## 6. Code Signing (Optional / Enterprise Distribution)

To sign the resulting binaries with an Authenticode digital certificate:

```powershell
$SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
$CertPath = $env:SIGNING_CERT_PATH
$CertPass = $env:SIGNING_CERT_PASSWORD

& $SignTool sign /f $CertPath /p $CertPass /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\EnergyAutomation\EnergyAutomation.exe"
& $SignTool sign /f $CertPath /p $CertPass /tr http://timestamp.digicert.com /td sha256 /fd sha256 "release\EnergyAutomation-2.0.0-Setup.exe"
```
