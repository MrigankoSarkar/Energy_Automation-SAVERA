# Chapter 6: API Contracts, Interfaces & DTO Specifications

This chapter defines the core service interfaces, Python `Protocol` contracts, and immutable Data Transfer Objects (DTOs) that form the clean architectural boundaries of EnergyAutomation.

---

## 1. Core Data Transfer Objects (DTOs)

All domain entities and cross-service payloads are modeled using standard Python `dataclasses`:

### 1. `MeterReading`
Represents an individual physical meter's telemetry snapshot:
```python
@dataclass
class MeterReading:
    meter_name: str
    active_energy_kwh: Optional[float]
    apparent_energy_kvah: Optional[float] = None
    reactive_energy_kvarh: Optional[float] = None
    power_factor: Optional[float] = None
    status: str = "VALID"  # VALID, N/A, OUT_OF_BOUNDS, COMMUNICATION_FAIL
    raw_unit: str = "kWh"
```

### 2. `ParsedReport`
Represents the complete parsed payload of an NBSense daily report:
```python
@dataclass
class ParsedReport:
    report_date: str                 # Format: YYYY-MM-DD
    source_filename: str
    file_hash_sha256: str
    readings: List[MeterReading]
    total_active_energy_kwh: float   # Target: 9,206.83 for 15-02-2026
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3. `ValidationResult`
Encapsulates deterministic validation results:
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_readings_count: int = 0
```

### 4. `Alert`
Encapsulates an operational notification or anomaly:
```python
@dataclass
class Alert:
    alert_id: str
    category: str        # CRITICAL, WARNING, INFO, AI_ADVISORY
    severity: str        # HIGH, MEDIUM, LOW
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
```

---

## 2. Abstract Service Interfaces (Protocols)

EnergyAutomation uses `typing.Protocol` to enforce interface contracts without tight inheritance hierarchies:

### `IPDFParser`
```python
class IPDFParser(Protocol):
    def parse_report(self, file_path: Path) -> ParsedReport:
        """Parses an NBSense PDF and returns a structured ParsedReport."""
        ...
```

### `IValidator`
```python
class IValidator(Protocol):
    def validate(self, report: ParsedReport) -> ValidationResult:
        """Applies mathematical and business validation rules to a report."""
        ...
```

### `IExcelService`
```python
class IExcelService(Protocol):
    def update_workbook(self, report: ParsedReport) -> bool:
        """Updates the configured Excel workbook with report readings."""
        ...
    
    def verify_integrity(self, row_idx: int) -> bool:
        """Verifies row 16 and row 4 formula integrity."""
        ...
```

### `IPersistenceRepo`
```python
class IPersistenceRepo(Protocol):
    def save_report(self, report: ParsedReport) -> int:
        """Persists report and meter readings idempotently. Returns report_id."""
        ...
    
    def get_report_by_date(self, report_date: str) -> Optional[ParsedReport]:
        """Retrieves a historical report by ISO date."""
        ...
```

### `IAlertService`
```python
class IAlertService(Protocol):
    def raise_alert(self, category: str, severity: str, title: str, message: str) -> Alert:
        """Generates and registers an operational alert."""
        ...
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marks an alert as acknowledged."""
        ...
```

---

## 3. Dependency Injection Container (`app/bootstrap/dependencies.py`)

The application bootstraps its services via a centralized inversion-of-control container:

```python
class Container:
    def __init__(self, config: AppConfig):
        self.config = config
        
        # 1. Base Infrastructure
        self.event_bus = EventBus()
        self.persistence_repo = SQLitePersistenceRepo(config.database.path)
        
        # 2. Domain Services
        self.pdf_parser = PDFParser(self.event_bus)
        self.validator = DataValidator(config.validation_rules)
        self.excel_service = ExcelService(config.excel, self.event_bus)
        self.alert_service = AlertService(self.event_bus)
        self.plant_topology = PlantTopologyService()
        self.powerbi_service = PowerBIService(config.powerbi)
        self.ai_service = GeminiAIService(config.ai)
        
        # 3. Application Orchestration
        self.workflow = WorkflowCoordinator(
            pdf_parser=self.pdf_parser,
            validator=self.validator,
            excel_service=self.excel_service,
            persistence=self.persistence_repo,
            alert_service=self.alert_service,
            plant_topology=self.plant_topology,
            powerbi_service=self.powerbi_service,
            event_bus=self.event_bus,
            config=self.config
        )
```
This decoupling enables unit testing each service with mock implementations in complete isolation, as demonstrated across the 49 test suites.
