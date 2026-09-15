# Architecture Reference: System Boundaries & Integration Specifications

This document serves as the technical reference for system architects, IT security directors, and enterprise integration leads.

---

## 1. Subsystem Decomposition & Boundaries

EnergyAutomation enforces strict separation between domain logic and presentation/infrastructure layers:

| Subsystem | Boundary Class | Primary Responsibility | Failure Isolation Strategy |
| :--- | :--- | :--- | :--- |
| **Presentation** | `ui.dashboard.Dashboard` | PySide6 desktop GUI shell, 12 views, simple/engineer toggle | Headless fallback supported via `with_ui=False` |
| **Event Bus** | `app.events.bus.EventBus` | In-process thread-safe pub/sub broker | Isolated try/except wrapping subscriber calls |
| **Orchestration**| `app.orchestration.workflow.AutomationWorkflow` | Sequential execution of retrieval, parsing, validation, and storage | Concurrency mutex lock (`WorkflowConcurrencyLock`) |
| **PDF Extraction**| `app.services.pdf.service.PDFService` | PyMuPDF tabular text tokenizer and unit normalizer | Deterministic regex; invalid tokens rejected |
| **Data Validation**| `app.services.validation.service.ValidationService` | Non-negative bounds, uniqueness, and reference checks | Zero heuristic guessing; corrupt reports abort |
| **Excel Ops** | `app.services.excel.service.ExcelService` | In-place updates, path sanitizer, formula verifier | Pre-write `.tmp` save + atomic OS file replace |
| **Persistence** | `app.persistence.repositories.report_repository.ReportRepository` | SQLite audit trail ledger, SHA-256 report deduplication | SQLite Write-Ahead Logging (WAL) mode |
| **Reconciliation**| `app.services.reconciliation.service.ReconciliationService` | 30-day missing date gap detector & weekend classifier | Chronological ordering; duplicate omission |
| **Power BI** | `app.services.powerbi.service.PowerBIService` | Star Schema CSV builder, DAX generator, REST push | Degrades gracefully to local CSV export |
| **AI Intelligence**| `app.services.ai.gemini_service.GeminiService` | Advisory natural-language Q&A and anomaly explanation | Strictly read-only; offline deterministic fallback |

---

## 2. Invariants & Mathematical Guarantees

1. **Target Energy Verification**:
   $$\sum_{i=1}^{18} E_{\text{active}, i} = 9,206.83\text{ kWh}$$
   This reference value is asserted in integration tests (`test_workflow_end_to_end_real_pdf_and_excel`).
2. **Formula Preservation**:
   - Cell `R16` contains `=SUM(C16:Q16)`.
   - Cell `R4` contains `=SUM(R5:R34)`.
   - Cell `C4` through `Q4` contain `=SUM(C5:C34)`.
3. **`N/A` Preservation**:
   $$\text{Status}(M_i) = \text{N/A} \implies E_i = \text{None} \quad (\text{Never } 0.0)$$

---

## 3. Data Flow Architecture

```text
[Gmail Inbox] ──(OAuth 2.0)──► [PDF Attachment] ──(PyMuPDF)──► [Parsed Readings]
                                                                        │
                                                                        ▼
                                                             [Deterministic Validator]
                                                                        │
                                   ┌────────────────────────────────────┼────────────────────────────────────┐
                                   ▼                                    ▼                                    ▼
                          [Excel Workbook]                    [SQLite Audit DB]                   [Plant Topology Map]
                      (Pre-write snapshot &                   (SHA-256 Hash &                      (7 Production Zones)
                        Atomic file swap)                       Telemetry Log)
```
