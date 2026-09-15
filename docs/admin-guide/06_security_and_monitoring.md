# Chapter 6: Security & System Monitoring

This chapter outlines enterprise security controls, secret masking policies, structured auditing, and observability infrastructure within EnergyAutomation.

---

## 1. Security Architecture & Threat Model

EnergyAutomation interacts with local filesystems, external email servers (Gmail), and cloud analytical APIs (Google Gemini, Microsoft Power BI).

### Security Principles
1. **Principle of Least Privilege**:
   - Gmail scope requested is strictly read-only: `gmail.readonly`. The application cannot send emails, delete messages, or alter mailbox filters.
   - Excel automation operates exclusively on configured workbook paths without accessing arbitrary system drives.
2. **Secret Redaction & Memory Protection**:
   - Google Gemini API keys and Azure Client Secrets are masked in application logs, UI text boxes, and debug outputs (`AIzaSy****...`).
   - Authentication tokens are never stored in plaintext log files or exported with Power BI datasets.

---

## 2. Structured Logging & Auditing

EnergyAutomation employs Python's standard `logging` library augmented with rotating file handlers and timestamped audit formatters:

### Log Files Directory (`logs/`)
- `logs/audit.log`: Comprehensive operational audit trail documenting every workflow trigger, PDF ingestion event, SHA-256 report hash, meter count, and Excel write confirmation.
- `logs/scheduler.log`: Background scheduling heartbeats, poll timestamps, and next-run calculations.
- `logs/errors.log`: Unhandled exceptions, stack traces, and network failure diagnostics.

### Sample Audit Log Entry
```text
2026-02-15 06:00:02.148 [INFO] [WorkflowCoordinator] Starting automated workflow execution. Trigger: Scheduled (06:00 AM)
2026-02-15 06:00:03.412 [INFO] [PDFParser] Parsed PDF: 2026-02-15.pdf | Hash: 8f4d92a1... | Meter Count: 18 | Total Energy: 9,206.83 kWh
2026-02-15 06:00:03.520 [INFO] [DataValidator] Validation PASSED (0 errors, 1 warning: Meter 14 active energy is N/A)
2026-02-15 06:00:04.102 [INFO] [ExcelService] Backup created: data/backups/Test_BI_Analysis_Report_2026_20260215_060004.xlsx
2026-02-15 06:00:04.890 [INFO] [ExcelService] Workbook updated: Row 16 (15-Feb-2026) | 18 meters mapped
2026-02-15 06:00:05.012 [INFO] [ExcelVerifier] Formula integrity PASSED (Row 16 =SUM(C16:Q16) intact)
2026-02-15 06:00:05.150 [INFO] [EventBus] Published event: WorkflowCompletedEvent (duration: 3.002s)
```

### Log Rotation Policy
Logs are rotated using `RotatingFileHandler` with a max size of **10 MB** per file and **5 rolling backup files** retained (`audit.log.1`, `audit.log.2`, etc.).

---

## 3. Health Checks & Observability

### Heartbeat & Status Endpoint
When running in background/daemon mode, EnergyAutomation tracks:
- **Last Ingestion Timestamp**: Precise datetime of the last successful report processing.
- **Workflow State**: `IDLE`, `RUNNING`, `ERROR`, or `RETRY_SCHEDULED`.
- **Active Alerts**: Unacknowledged `CRITICAL` or `WARNING` alerts held in `AlertService`.

### Windows Event Log Integration
In high-security enterprise environments, IT administrators can forward EnergyAutomation critical events to the **Windows Event Log (Application Log)**:
```powershell
# PowerShell script to inspect application log events for EnergyAutomation
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='EnergyAutomation'} -MaxEvents 50
```

---

## 4. Compliance Checklist

- [x] No hardcoded passwords or API keys in source code repository.
- [x] All `.gitignore` rules active for `credentials.json`, `token.pickle`, and `.env`.
- [x] Deterministic validation rules reject negative, out-of-range, or corrupted values before any persistent write occurs.
- [x] Complete rollback capability for all spreadsheet modifications.
- [x] Offline execution mode available for air-gapped industrial manufacturing plants.
