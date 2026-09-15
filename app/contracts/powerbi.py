from dataclasses import dataclass, field

@dataclass
class PowerBIResult:
    success: bool
    operation: str
    message: str = ''
    details: dict = field(default_factory=dict)
