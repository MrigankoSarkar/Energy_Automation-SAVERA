from dataclasses import dataclass
from datetime import date
@dataclass
class ReportRecord:
    message_id:str
    report_date:date
    filename:str
    status:str
