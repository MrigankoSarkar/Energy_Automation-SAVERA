from __future__ import annotations

from datetime import datetime

from config import get_excel_path
from excel_service import update_existing_workbook


def run_excel_update(
    config,
    report_date,
    pending,
):

    workbook_path = get_excel_path(config)

    print("=" * 70)
    print("[EXCEL] Dynamic workbook resolution")
    print(f"[EXCEL] Configured path : {config['excel']['file']}")
    print(f"[EXCEL] Resolved path   : {workbook_path}")
    print("=" * 70)

    if not workbook_path.exists():
        raise RuntimeError(
            f"EXCEL-001: Workbook not found: {workbook_path}"
        )

    result = update_existing_workbook(
        workbook_path=workbook_path,

        worksheet_name=config["excel"]["worksheet"],

        report_date=report_date,

        meters=pending,

        header_row=config["excel"].get(
            "header_row",
            3
        ),

        date_column=config["excel"].get(
            "date_column",
            2
        ),

        first_data_row=config["excel"].get(
            "first_data_row",
            5
        ),

        total_column=config["excel"].get(
            "total_column",
            18
        ),

        update_total=config["excel"].get(
            "update_total",
            True
        ),

        fail_on_unmapped_numeric_meter=config[
            "excel"
        ].get(
            "fail_on_unmapped_numeric_meter",
            False
        ),
    )

    return result