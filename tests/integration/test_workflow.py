from datetime import date
from pathlib import Path
import shutil
import openpyxl
import pytest

from app.orchestration.workflow import AutomationWorkflow
from app.services.pdf.parser import PDFParser
from app.services.validation.service import ValidationService
from app.services.reconciliation.service import ReconciliationService
from app.services.excel.service import ExcelService
from app.persistence.database import Database
from app.persistence.repositories.report_repository import ReportRepository


SAMPLE_PDF = Path("data/pdfs/report_2026-09-11_2026-09-12.pdf").resolve()
ORIGINAL_EXCEL = Path("Test_BI_Analysis_Report_2026.xlsx").resolve()


class MockGmailRepository:
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def find_reports(self):
        return [
            {
                "id": "msg_001",
                "subject": "NBSense EMS Monitoring Report - 2026-09-12",
                "file_path": str(self.pdf_path),
            }
        ]


def test_workflow_end_to_end_real_pdf_and_excel(tmp_path):
    """End-to-end integration test of AutomationWorkflow using real PDF and real Excel copy."""
    assert SAMPLE_PDF.exists(), f"Sample PDF missing: {SAMPLE_PDF}"
    assert ORIGINAL_EXCEL.exists(), f"Original Excel missing: {ORIGINAL_EXCEL}"

    # 1. Prepare isolated test Excel copy
    test_excel = tmp_path / "Test_Workbook.xlsx"
    shutil.copy2(ORIGINAL_EXCEL, test_excel)

    # 2. Prepare isolated test SQLite database
    test_db_path = tmp_path / "test_automation.db"
    db = Database(str(test_db_path))
    db.connect()
    db.initialize()
    repo = ReportRepository(db)

    # 3. Instantiate real services
    pdf_parser = PDFParser()
    validation_service = ValidationService()
    excel_service = ExcelService(
        file_path=str(test_excel),
        sheet_name="EMS Monitoring Report",
    )
    reconciliation_service = ReconciliationService(excel_service=excel_service)
    gmail_repo = MockGmailRepository(SAMPLE_PDF)

    # 4. Build workflow
    workflow = AutomationWorkflow(
        gmail_service=None,
        gmail_repository=gmail_repo,
        pdf_service=pdf_parser,
        validation_service=validation_service,
        reconciliation_service=reconciliation_service,
        excel_service=excel_service,
        energy_analyzer=None,
        ai_decision_engine=None,
        powerbi_service=None,
        powerbi_publisher=None,
        powerbi_refresh=None,
        notification_service=None,
        repository=repo,
    )

    # 5. Execute workflow
    result = workflow.run()

    # 6. Verify workflow execution output
    assert result["success"] is True, f"Workflow failed: {result}"
    assert result["status"] == "completed"
    assert len(result["processed"]) == 1
    proc = result["processed"][0]
    assert proc["success"] is True
    excel_res = proc["excel"]
    assert excel_res.success is True
    # 15 meter cells + 1 Total formula cell = 16 cells updated
    assert len(excel_res.updated_cells) == 16
    assert "R16" in excel_res.updated_cells
    assert pytest.approx(excel_res.total_value, rel=1e-4) == 9206.83

    # 7. Verify Excel workbook content and formulas
    wb = openpyxl.load_workbook(test_excel, data_only=False)
    sheet = wb["EMS Monitoring Report"]

    # Verify row 16 date
    cell_date = sheet.cell(row=16, column=2).value
    # Could be datetime or date or string matching 2026-09-12
    if hasattr(cell_date, "strftime"):
        assert cell_date.strftime("%Y-%m-%d") == "2026-09-12"
    else:
        assert str(cell_date).startswith("2026-09-12")

    # Verify row 16 total formula
    total_formula = sheet.cell(row=16, column=18).value
    assert total_formula == "=SUM(C16:Q16)"

    # Verify row 4 cumulative YTD formulas remain intact
    assert sheet.cell(row=4, column=3).value == "=SUM(C5:C35)" or sheet.cell(row=4, column=3).value.startswith("=SUM")
    assert sheet.cell(row=4, column=18).value == "=SUM(R5:R34)" or sheet.cell(row=4, column=18).value.startswith("=SUM")

    # Verify row 16 values in openpyxl with data_only=False
    # Columns C (3) to Q (17)
    meter_values = []
    for col in range(3, 18):
        v = sheet.cell(row=16, column=col).value
        if v is not None:
            meter_values.append(v)

    # We expect 15 mapped readings totaling 9206.83
    assert len(meter_values) == 15
    numeric_sum = sum(meter_values)
    assert pytest.approx(numeric_sum, rel=1e-4) == 9206.83

    wb.close()

    # 8. Verify SQLite persistence
    reports = repo.get_reports()
    assert len(reports) == 1
    assert reports[0]["report_date"] == "2026-09-12"

    readings = repo.get_readings_for_report(reports[0]["id"])
    assert len(readings) == 18

    # Verify N/A meter reading preserved as N/A and not 0.0
    raskog = next(r for r in readings if "RASKOG" in r["meter_name"])
    assert raskog["status"] == "N/A"
    assert raskog["active_energy"] is None
