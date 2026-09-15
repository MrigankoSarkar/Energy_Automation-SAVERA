# Chapter 3: Scheduler & Background Automation

This chapter details the background task scheduling architecture, system tray minimization, concurrency controls, and headless Windows Task Scheduler deployment options for EnergyAutomation.

---

## 1. Built-in Scheduling Engine

EnergyAutomation embeds an in-process scheduling service (`app/scheduler/service.py`) built with `APScheduler` (Advanced Python Scheduler).

### Key Features
- **Daily Cron Triggers**: Executes the automated ingestion pipeline at a designated morning hour (default: `06:00 AM`), immediately after NBSense compiles the previous 24-hour facility shift.
- **Interval Polling Fallback**: Optional periodic inbox polling (e.g. every 15 minutes) to detect delayed email arrivals during network hiccups.
- **Concurrency Locking**: Utilizes an atomic thread lock (`threading.Lock`) ensuring that manual "Run Now" clicks or overlapping scheduled triggers never execute simultaneously. If a run is already active, subsequent triggers log an `ExecutionBusy` notice and safely exit.

---

## 2. System Tray Minimization & Background Execution

To prevent plant operators from accidentally closing the automation window, EnergyAutomation includes full Windows System Tray integration:

### System Tray Behaviors
1. **Minimize to Tray**: When the user clicks the standard window minimize button or closes the window with background mode enabled, the window hides into the system notification area (near the Windows clock).
2. **Tray Context Menu**:
   - **Show Dashboard**: Restores and focuses the main application window.
   - **Run Workflow Now**: Manually triggers an immediate ingestion cycle in the background.
   - **Status Indicator**: Displays current status (`Idle`, `Running`, or `Error`).
   - **Exit Application**: Completely shuts down the application, cleanly terminating background threads and database connections.
3. **Balloon / Toast Notifications**: System tray bubbles notify the operator when:
   - A report is successfully processed (`"NBSense report for 15-02-2026 ingested. Total: 9,206.83 kWh"`).
   - An alert condition is raised (`"Critical Alert: Incomer load exceeded peak threshold"`).

---

## 3. Headless Enterprise Deployment (Windows Task Scheduler)

For unmanned server environments or dedicated SCADA/EMS VMs where no user logs into a desktop session, EnergyAutomation can be scheduled via native **Windows Task Scheduler** in headless mode.

### Command-Line Arguments
EnergyAutomation supports command-line flags:
- `python run.py --headless`: Runs the full pipeline once synchronously and exits with code `0` on success or non-zero on failure.
- `python run.py --headless --date 2026-02-15`: Runs ingestion specifically targeting the specified report date.
- `python run.py --export-powerbi`: Generates all Power BI Star Schema CSVs, DAX measures, and JSON schemas without opening the GUI.

### Creating the Windows Scheduled Task via PowerShell
Run this administrative PowerShell command to create a daily task triggered at 06:15 AM:

```powershell
$Action = New-ScheduledTaskAction `
    -Execute "C:\Savera_EMS\EnergyAutomation\.venv\Scripts\python.exe" `
    -Argument "run.py --headless" `
    -WorkingDirectory "C:\Savera_EMS\EnergyAutomation"

$Trigger = New-ScheduledTaskTrigger -Daily -At 06:15AM

$Principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName "Savera_EnergyAutomation_DailySync" `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Automated daily NBSense EMS ingestion and Excel update for Savera MS"
```

---

## 4. Monitoring & Task Health Checks

- **Exit Codes**:
  - `0`: Ingestion completed successfully, Excel formulas verified, SQLite audit logged.
  - `1`: Validation error (e.g. negative energy or schema mismatch in PDF).
  - `2`: File lock or filesystem error (e.g. Excel open by user).
  - `3`: Network or credential authentication failure.
- **Log Files**: All execution output is captured in `logs/audit.log` and `logs/scheduler.log` with microsecond-resolution timestamps.
