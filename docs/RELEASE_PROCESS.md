# EnergyAutomation — Release Process & Versioning Guide

This document defines the repeatable release procedure for issuing patch, minor, and major updates of **EnergyAutomation**.

---

## 1. Versioning Standard

EnergyAutomation follows [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR (`X.0.0`)**: Incompatible changes to database schema or workbook contracts.
- **MINOR (`0.X.0`)**: New feature additions, new subinterfaces, backwards-compatible enhancements.
- **PATCH (`0.0.X`)**: Bug fixes, performance improvements, packaging adjustments.

---

## 2. Release Steps

### Step 1: Update Single Source of Truth
Edit `app/version.py`:
```python
APP_VERSION = "2.0.1"
APP_VERSION_TUPLE = (2, 0, 1, 0)
```

### Step 2: Synchronize Windows PE Version File
Update `installer/file_version_info.txt`:
```python
filevers=(2, 0, 1, 0),
prodvers=(2, 0, 1, 0),
...
StringStruct('FileVersion', '2.0.1.0'),
StringStruct('ProductVersion', '2.0.1.0')
```

### Step 3: Synchronize Inno Setup Script
In `installer/EnergyAutomation.iss`:
```inno
#define MyAppVersion "2.0.1"
```

### Step 4: Run Automated Build Pipeline
Run the PowerShell build pipeline:
```powershell
.\scripts\build_windows.ps1
```

This runs:
- `pytest` test suite validation
- `compileall` syntax validation
- Standalone PyInstaller compile
- Portable archive `.zip` bundling
- Inno Setup installer compilation

### Step 5: Smoke Test Artifacts
Before publishing the release:
1. Run `dist\EnergyAutomation\EnergyAutomation.exe`.
2. Confirm GUI loads, subinterfaces navigate, and theme is active.
3. Test installer in test sandbox: `release\EnergyAutomation-2.0.1-Setup.exe`.
4. Confirm Start Menu and Desktop shortcuts work.

### Step 6: Git Tagging & Release Notes
```bash
git add app/version.py installer/file_version_info.txt installer/EnergyAutomation.iss
git commit -m "chore(release): bump version to 2.0.1"
git tag -a v2.0.1 -m "Release v2.0.1"
git push origin main --tags
```
Publish `release/EnergyAutomation-2.0.1-Setup.exe` and `release/EnergyAutomation-2.0.1-win64.zip` to the release distribution channel.
