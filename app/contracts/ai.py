from dataclasses import dataclass, field

@dataclass
class AIAnalysis:
    severity: str = 'INFO'
    category: str = 'NORMAL'
    confidence: float = 0.0
    message: str = ''
    recommended_action: str = ''
    requires_human_review: bool = False
    raw_response: str = ''
    metadata: dict = field(default_factory=dict)
