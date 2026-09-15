from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

@dataclass(frozen=True)
class ReportArtifact:
    message_id: str
    thread_id: str
    received_at: Optional[datetime]
    filename: str
    path: str

@dataclass(frozen=True)
class EnergyReading:
    meter_name: str
    active_energy: Optional[float]
    unit: str = 'kWh'
    status: str = 'OK'
    page_number: Optional[int] = None

@dataclass
class EnergyReport:
    report_date: date
    source_message_id: str
    source_filename: str
    received_at: Optional[datetime]
    readings: list[EnergyReading] = field(default_factory=list)

@dataclass
class ValidatedEnergyReport:
    report: EnergyReport
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unmapped_numeric_meters: list[str] = field(default_factory=list)
