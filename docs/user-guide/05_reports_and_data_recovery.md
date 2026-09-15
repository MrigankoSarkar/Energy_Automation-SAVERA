# EnergyAutomation — User Guide: Reports & Data Recovery

## 1. Reports & Audit Trail Ledger
Under **Reports & Audit**, the application displays an immutable historical record of every processed EMS report stored in the SQLite database:
- **Report Date**: Target date represented by the report telemetry.
- **Attachment**: Original filename of the downloaded PDF.
- **Status**: `COMPLETED` or `FAILED`.
- **Total Energy (kWh)**: Sum of all verified active energy readings.
- **Meters (Mapped / Total)**: Ratio of meters successfully mapped into Excel columns (e.g. `15/18`).
- **Excel Status**: Confirmation of workbook update.
- **Power BI**: Status of analytical synchronization (`SYNCED`, `PENDING`, or `DISABLED`).
- **Processed At**: Local timestamp when processing occurred.

---

## 2. Historical Data Recovery & Weekend Gap Healing

### Why Is Recovery Necessary?
In industrial manufacturing facilities:
1. Monitoring computers may be powered down over the weekend.
2. Reports for Saturday and Sunday might arrive on Monday morning.
3. Network outages can cause delayed email deliveries.

### How It Works:
- EnergyAutomation automatically executes a **30-day reconciliation scan** on every scheduled run.
- It compares the dates in your Excel workbook against the calendar up to 30 days in the past.
- If missing dates are detected, it queries Gmail specifically for reports matching those dates.
- Recovered reports are processed **chronologically** to maintain contiguous monthly records.

### Manual Gap Recovery:
1. Navigate to **Data Recovery** on the sidebar.
2. Click **Scan for Missing Dates (30 Days)** to review any gaps.
3. Click **Run Historical Gap Healing Now** to trigger automated download, parsing, validation, and Excel updates.
