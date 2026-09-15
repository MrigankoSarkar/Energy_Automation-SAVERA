from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MeterResult:
    meter_name: str
    excel_header: Optional[str]
    active_energy: Optional[float]
    status: str
    reason: Optional[str] = None
