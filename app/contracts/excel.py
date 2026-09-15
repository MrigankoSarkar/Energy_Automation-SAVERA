from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ExcelUpdateResult:
    success: bool
    workbook: str
    worksheet: str
    report_date: str
    updated_cells: list[str] = field(default_factory=list)
    skipped_meters: list[str] = field(default_factory=list)
    total_value: Optional[float] = None
    message: str = ''
