# EnergyAutomation — Installation & Deployment Guide

This guide describes how end users, system administrators, and plant operators install, configure, upgrade, and uninstall **EnergyAutomation** on Windows 11.

---

## 1. System Requirements

- **Operating System**: Windows 11 (22H2 or newer) or Windows 10 (64-bit).
- **Architecture**: x86_64 / AMD64.
- **RAM**: 4 GB minimum (8 GB recommended).
- **Disk Space**: ~350 MB for installation, plus storage for downloaded PDF reports and audit databases.
- **Python Runtime**: **NOT REQUIRED**. All Python runtimes, Qt libraries, and dependencies are self-contained.

---

## 2. Standard Installation

1. Download or locate `EnergyAutomation-2.0.0-Setup.exe` from the `release/` directory.
2. Double-click `EnergyAutomation-2.0.0-Setup.exe`.
3. Follow the Setup Wizard steps:
   - **Installation Location**: Defaults to `{autopf}\EnergyAutomation` (e.g. `C:\Program Files\EnergyAutomation`).
   - **Shortcuts**: Check the box to create a **Desktop shortcut** if desired.
4. Click **Install**.
5. On the completion screen, check **Launch EnergyAutomation** and click **Finish**.

---

## 3. Silent / Unattended Installation (IT Deployment)

System administrators can deploy EnergyAutomation across plant workstations silently via Microsoft Intune, Group Policy (GPO), or PowerShell:

```powershell
EnergyAutomation-2.0.0-Setup.exe /VERYSILENT /NORESTART /SP- /MERGETASKS="!desktopicon"
```

---

## 4. User Data Architecture & Storage

To adhere to Microsoft Windows Enterprise Application guidelines, mutable data is strictly kept out of `Program Files` and stored in the user profile:

| Directory | Location | Purpose |
| :--- | :--- | :--- |
| **Configuration** | `%LOCALAPPDATA%\EnergyAutomation\Config` | User settings (`settings.json`) |
| **Audit Database** | `%LOCALAPPDATA%\EnergyAutomation\Database` | SQLite audit trail (`automation.db`) |
| **Logs** | `%LOCALAPPDATA%\EnergyAutomation\Logs` | Application execution logs |
| **Backups** | `%LOCALAPPDATA%\EnergyAutomation\Backups` | Excel workbook timestamped backups |
| **Reports** | `%LOCALAPPDATA%\EnergyAutomation\Reports` | Downloaded NBSense PDF reports |
| **Credentials** | `%LOCALAPPDATA%\EnergyAutomation\Credentials`| Google OAuth tokens |

---

## 5. First-Run Setup Experience

When EnergyAutomation starts for the first time:
1. The **Initial Setup Wizard** appears automatically.
2. Step 1: Welcome & Plant Overview.
3. Step 2: Excel Workbook Selection. Select your plant's `BI_Analysis_Report_2026.xlsx` or browse to a shared network drive.
4. Step 3: Gmail Integration setup.
5. Step 4: AI advisory model configuration (optional Gemini API key).
6. Step 5: Plotly Dash BI integration confirmation.
7. Step 6: Database connectivity test.
8. Step 7: System validation review.
9. Step 8: Setup complete!

---

## 6. Upgrading to a New Version

When upgrading (e.g. from `2.0.0` to `2.0.1`):
1. Run the new `EnergyAutomation-Setup.exe`.
2. The installer automatically detects the existing installation, upgrades all application binaries, and **preserves all user configuration, SQLite databases, and downloaded reports**.

---

## 7. Uninstallation

To uninstall EnergyAutomation:
1. Open **Windows Settings** -> **Apps** -> **Installed apps**.
2. Find **EnergyAutomation**.
3. Click the three dots `...` and choose **Uninstall**.
4. The uninstaller removes all program binaries, Start Menu shortcuts, and Desktop shortcuts.
5. **Data Preservation Prompt**: The uninstaller will ask whether you wish to keep your user configuration, audit database, and reports (`%LOCALAPPDATA%\EnergyAutomation`). Choose **No** to preserve your business data, or **Yes** to completely remove everything.
