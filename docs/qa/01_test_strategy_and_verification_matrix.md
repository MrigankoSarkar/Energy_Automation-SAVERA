# QA Strategy & Production Verification Matrix

This document outlines the testing strategy, test automation suites, regression safeguards, and production acceptance criteria for EnergyAutomation.

---

## 1. Testing Philosophy & Test Levels

EnergyAutomation employs a multi-tiered test pyramid ensuring both high execution speed and comprehensive verification:

```text
               / \
              /   \
             / E2E \       (2 tests: Headless bootstrap, Qt Dashboard wiring)
            /-------\
           / Integr. \     (2 tests: Workflow real PDF+Excel, Idempotency)
          /-----------\
         /    Unit     \   (45 tests: Parser, Excel, Persistence, Alerts, AI, Topology)
        /---------------\
```

### Invariant Rules for Testing
- **Production Isolation**: Tests must **never** overwrite or mutate the live production spreadsheet `Test_BI_Analysis_Report_2026.xlsx`. All write tests use `tmp_path` copies.
- **Mocking External APIs**: Network-dependent APIs (Gmail Google API, Power BI Azure REST API, Gemini AI Cloud API) must use test doubles or verify local fallback paths during CI test runs.
- **Formula Verification**: Every test writing to an Excel workbook must assert that formula strings (e.g. `=SUM(C16:Q16)`) remain in formula syntax rather than being converted to static scalar numbers.

---

## 2. Complete Test Suite Matrix

| Suite File | Tests | Focus Area | Status |
| :--- | :--- | :--- | :--- |
| `tests/end_to_end/test_application_e2e.py` | 2 | Headless application bootstrap, scheduler state, PySide6 offscreen GUI wiring across 12 views, mode toggle, search, tour dialog, wizard dialog | **PASS** |
| `tests/integration/test_workflow.py` | 1 | Real 18-page PDF parsing, validation, Excel row 16 update, 9,206.83 kWh sum verification | **PASS** |
| `tests/integration/test_idempotency.py` | 1 | Ingesting identical report twice; asserts in-place update without row duplication | **PASS** |
| `tests/unit/test_excel_service.py` | 5 | Header discovery, existing dates, row update, formula verification, path normalization safety | **PASS** |
| `tests/unit/test_pdf_parser.py` | 5 | Tabular parsing, multi-page reports, missing files, N/A normalization, MWh to kWh conversions | **PASS** |
| `tests/unit/test_validation.py` | 6 | Valid report, N/A preservation, negative energy rejection, extreme energy threshold, duplicate meters, unit checks | **PASS** |
| `tests/unit/test_persistence.py` | 3 | SQLite save/query, idempotent duplicate ingestion, audit trail columns and statistics | **PASS** |
| `tests/unit/test_plant_topology.py` | 1 | 7 manufacturing zones, baseline capacity calculation, 18-meter aggregation | **PASS** |
| `tests/unit/test_alert_service.py` | 2 | Alert raising, category filtering, unacknowledged querying, workflow evaluation rules | **PASS** |
| `tests/unit/test_event_bus.py` | 3 | Thread-safe pub/sub, subscriber error isolation, wildcard matching, in-memory history | **PASS** |
| `tests/unit/test_powerbi.py` | 2 | Disabled by default safety, executive dataset JSON compilation | **PASS** |
| `tests/unit/test_powerbi_model.py` | 1 | Star schema CSV exports (Fact/Dims), measures.dax generation, schema validation | **PASS** |
| `tests/unit/test_reconciliation.py` | 5 | Date reconciliation, missing dates detection, weekend/Sunday classification, Friday-to-Monday gap healing | **PASS** |
| `tests/unit/test_scheduler.py` | 4 | APScheduler state, run now trigger, start/stop lifecycle, workflow concurrency mutex | **PASS** |
| `tests/unit/test_ai_intelligence.py` | 4 | Gemini advisory prompt rules, total energy query, top meters query, offline deterministic fallback | **PASS** |
| `tests/unit/test_core.py` | 4 | Date parsing, meter entity, column mapper, basic validation logic | **PASS** |
| **TOTAL** | **49** | **Complete System Regression & Hardening** | **100% PASS** |

---

## 3. Production Readiness Sign-Off Criteria

- [x] Zero regressions across all 49 test cases.
- [x] Excel row 16 formula `=SUM(C16:Q16)` verified intact.
- [x] Row 4 cumulative formulas `=SUM(R5:R34)` and `=SUM(C5:C34)` verified read-only.
- [x] Target active energy verified at exactly 9,206.83 kWh.
- [x] All 18 meters mapped with zero unmapped numeric meters.
- [x] `N/A` meters preserved as `N/A` (never coerced to `0.0`).
- [x] Excel path normalization permanently eliminates nested quote bug.
- [x] In-process EventBus provides complete subscriber failure isolation.
- [x] UI/UX delivers modern Google-inspired desktop shell with collapsible sidebar.
- [x] Non-technical friendly error dialogs with "View Technical Details" for engineers.
- [x] Comprehensive 13-guide Help Center with interactive Guided Tour and Setup Wizard.
- [x] `.gitignore` and `.env.example` prevent secret leakage.
