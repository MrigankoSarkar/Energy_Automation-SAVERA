# EnergyAutomation — Troubleshooting & Installation FAQ

Common installation, startup, and runtime questions for **EnergyAutomation** on Windows 11.

---

## 1. Windows SmartScreen or Defender Warning

### Symptom:
"Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting."

### Cause:
The binary is new or not yet signed by an enterprise extended validation (EV) certificate trusted by Microsoft SmartScreen.

### Resolution:
1. Click **More info**.
2. Click **Run anyway**.
3. For enterprise deployment, sign both `EnergyAutomation.exe` and `EnergyAutomation-Setup.exe` using your organization's digital certificate via `signtool.exe` (see `docs/WINDOWS_BUILD.md`).

---

## 2. "Excel workbook not configured or not found"

### Symptom:
A notification banner indicates: *"Excel workbook path requires configuration."*

### Resolution:
1. Open the application.
2. In the left navigation bar, click **Settings** (or click **Initial Setup Wizard** on the Overview screen).
3. Under **Excel Workbook Path**, click **Browse** and select your plant's `BI_Analysis_Report_2026.xlsx`.
4. Click **Save Settings**.

---

## 3. "Gmail requires authentication"

### Symptom:
Gmail status displays as *Authentication Required*.

### Resolution:
1. Place your Google API `credentials.json` into:
   `%LOCALAPPDATA%\EnergyAutomation\Credentials\`
2. Navigate to **Settings** -> **Gmail Integration** and click **Authenticate**.
3. Complete the Google browser authentication flow once. The resulting `token.json` will be stored securely in the user's `%LOCALAPPDATA%` credentials directory.

---

## 4. Application Does Not Start / Silent Exit

### Diagnostic Steps:
1. Check the application log file located at:
   `%LOCALAPPDATA%\EnergyAutomation\Logs\energy_automation.log`
2. If the application exits before initializing logs, build and run the debug executable:
   ```powershell
   .\scripts\build_windows_debug.ps1
   .\dist\EnergyAutomation_Debug\EnergyAutomation_Debug.exe
   ```
   The terminal window will display the full traceback and missing dependency.

---

## 5. Antivirus False Positives with PyInstaller

### Prevention:
PyInstaller executables are sometimes flagged by heuristic scanners. To minimize false positives:
- The build script uses the official PyInstaller distribution with standard UPX compression disabled (`upx=False`).
- Digital Authenticode signing resolves 99% of heuristic antivirus flags.
