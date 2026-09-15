# Chapter 5: Backups & Disaster Recovery

Data resilience and zero-loss guarantees are fundamental to EnergyAutomation. This chapter details backup mechanics, rolling retention rules, and step-by-step disaster recovery procedures.

---

## 1. Backup Strategy Overview

EnergyAutomation implements a two-tier automated backup architecture:

```text
Incoming Report Ingestion
        │
        ├──► 1. Pre-Write Excel Snapshot ────► data/backups/Test_BI_Analysis_Report_2026_YYYYMMDD_HHMMSS.xlsx
        │                                      (Atomic copy before openpyxl touch)
        │
        └──► 2. SQLite Database Journal ─────► data/energy_audit.db (WAL Mode)
                                               Periodic snapshot to data/backups/energy_audit_backup.db
```

### Key Guarantees
1. **Zero Overwrite Without Backup**: The workbook `Test_BI_Analysis_Report_2026.xlsx` is never modified until a timestamped snapshot is successfully written and verified on disk.
2. **Atomic Temp File Writes**: Modifications are written to a hidden `.tmp` file in the same directory. Only after `openpyxl` completes writing and closes cleanly is the file renamed over the live file. If a power failure occurs during saving, the live workbook remains completely untouched.
3. **Retention Rotation**: The backup manager keeps the last 30 snapshots by default, automatically purging older files to prevent disk exhaustion while maintaining full monthly rollbacks.

---

## 2. Restoring an Excel Workbook from Backup

If a user accidentally damages the production spreadsheet (e.g. deleting columns, overwriting formulas, or applying incorrect formatting):

### Step-by-Step Excel Restoration Procedure
1. **Close all instances of Microsoft Excel** on the workstation.
2. Open Windows File Explorer and navigate to:
   ```text
   C:\Savera_EMS\EnergyAutomation\data\backups\
   ```
3. Locate the snapshot taken immediately prior to the incident (e.g. `Test_BI_Analysis_Report_2026_20260215_060002.xlsx`).
4. Copy the file into the project root:
   ```powershell
   Copy-Item "C:\Savera_EMS\EnergyAutomation\data\backups\Test_BI_Analysis_Report_2026_20260215_060002.xlsx" -Destination "C:\Savera_EMS\EnergyAutomation\Test_BI_Analysis_Report_2026.xlsx" -Force
   ```
5. In EnergyAutomation, go to **Excel Operations** -> **Verify Formula Integrity**.
6. Ensure that Row 16 and Row 4 cumulative formulas report `100% OK`.

---

## 3. SQLite Database Recovery & Maintenance

The SQLite database (`data/energy_audit.db`) stores report hashes, audit records, reconciliation gaps, and alert logs.

### Database Maintenance
The database runs in `WAL` (Write-Ahead Logging) mode, enabling concurrent reads while writing. To perform a clean administrative backup of SQLite without stopping the application:

```powershell
# Using sqlite3 CLI tool
sqlite3 "C:\Savera_EMS\EnergyAutomation\data\energy_audit.db" ".backup 'C:\Savera_EMS\EnergyAutomation\data\backups\energy_audit_snapshot.db'"
```

### Recovering from SQLite Corruption
If the SQLite file is corrupted due to an abnormal hard reset or hardware disk failure:
1. Stop EnergyAutomation.
2. Rename the damaged file:
   ```powershell
   Move-Item "data\energy_audit.db" "data\energy_audit_corrupt.db"
   ```
3. Copy the latest clean snapshot from `data/backups/energy_audit_snapshot.db` to `data/energy_audit.db`.
4. If no snapshot exists, delete the corrupted file and launch EnergyAutomation. The system will automatically recreate the database schema and tables.
5. In the GUI, navigate to **Data Recovery & Manual Upload** (`Ctrl+6`) and re-ingest the month's archived PDFs from `data/reports/` to rebuild the audit tables completely.

---

## 4. Disaster Recovery Drill (RTO & RPO)

| Metric | Target | Verified Actual |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | $\le$ 24 hours | 0 hours (Pre-write snapshots guarantee immediate preceding state) |
| **Recovery Time Objective (RTO)** | < 15 minutes | < 2 minutes (Copy-paste single snapshot) |
