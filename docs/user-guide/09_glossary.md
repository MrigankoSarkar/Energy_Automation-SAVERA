# Chapter 9: Glossary of Terms & Electrical Abbreviations

This glossary defines electrical engineering terms, facility automation abbreviations, software concepts, and Power BI dimensional terminology used throughout EnergyAutomation.

---

## 1. Electrical & Facility Engineering Terms

| Term / Acronym | Definition |
| :--- | :--- |
| **Active Energy (kWh)** | The actual electrical energy consumed to perform useful mechanical or thermal work (e.g. driving motors, running heaters, powering CNC machines). Measured in kilowatt-hours (kWh) or megawatt-hours (MWh). |
| **Apparent Energy (kVAh)** | The vector sum of active power and reactive power. Represents the total electrical power delivered by the utility grid. |
| **Reactive Energy (kVARh)** | Energy absorbed and returned by inductive loads (motors, transformers, ballasts) to sustain magnetic fields. High reactive power leads to poor power factor. |
| **Power Factor (PF)** | The ratio of active energy to apparent energy ($\text{PF} = \frac{\text{kWh}}{\text{kVAh}}$). Ranging from 0.0 to 1.0 (unity). Industrial penalties occur if average monthly PF falls below utility thresholds (typically < 0.90 or 0.95). |
| **Maximum Demand (MD)** | The highest average power (kVA or kW) registered during any 15-minute or 30-minute integration period in a billing cycle. |
| **Incomer** | The primary medium-voltage (MV) or low-voltage (LV) feeder panel receiving bulk electricity directly from the utility substation or step-down transformer into the plant. |
| **PDB (Power Distribution Board)** | Electrical switchgear enclosures that distribute high-current power to specific shop floor machines, machining cells, or heavy motor control centers. |
| **MLDB (Main Lighting Distribution Board)** | Distribution panel dedicated strictly to lighting fixtures, emergency illumination, and peripheral small power sockets. |
| **APFC (Automatic Power Factor Correction)** | A capacitor bank panel with automated micro-controllers that switches capacitor stages in and out to maintain power factor near unity (~0.98 - 0.99). |
| **Specific Energy Consumption (SEC)** | Energy consumed per unit of production output (e.g., $\text{kWh}/\text{tonne}$ of steel pressed or $\text{kWh}/\text{unit}$ produced). |

---

## 2. NBSense & Energy Automation Software Concepts

| Term | Definition |
| :--- | :--- |
| **NBSense EMS** | The proprietary plant-wide Energy Management System hardware and software deployed on the factory floor that polls RS-485 Modbus power meters and generates daily PDF reports. |
| **Deterministic Validation** | Strict rule-based data verification where incoming values are checked against mathematical invariants (e.g., $E \ge 0$, no duplicate meters, correct units) without relying on heuristic guesses or AI speculation. |
| **Idempotency** | The property where executing the same operation multiple times produces the exact same result as executing it once. Ingesting the same PDF report twice will not duplicate rows or increment cumulative sums twice. |
| **EventBus** | An in-process publish-subscribe messaging architecture that decouples subsystems (e.g., notifying the UI, Alert Center, and Power BI when a PDF is parsed) while providing complete failure isolation. |
| **Data Reconciliation** | The automated verification process that compares expected chronological dates against ingested dates to identify missing shift reports, weekend gaps, or communication dropouts. |
| **Atomic File Write** | A file-saving technique where data is written to a temporary `.tmp` file and then renamed over the target file in a single OS filesystem operation, preventing file corruption during power outages or unexpected crashes. |

---

## 3. Power BI & Business Intelligence Terms

| Term | Definition |
| :--- | :--- |
| **Star Schema** | A relational data modeling technique where a central table of quantitative events (**Fact Table**) connects directly to surrounding context tables (**Dimension Tables**). |
| **Fact Table (`Fact_EnergyConsumption`)** | The core quantitative table containing numeric energy measurements, timestamps, power factors, and foreign keys for each meter reading. |
| **Dimension Table (`Dim_Meter`, `Dim_Date`, `Dim_Area`)** | Reference tables containing descriptive attributes (e.g. meter category, rated kW, shop floor zone, day of week, fiscal quarter) used to slice and dice facts. |
| **DAX (Data Analysis Expressions)** | The native formula and query language of Microsoft Power BI, Microsoft Fabric, and SSAS used to define custom business calculations and dynamic KPIs. |
| **Push Dataset** | A Power BI Service cloud dataset populated in real time via Microsoft REST APIs without requiring an on-premises data gateway. |
| **Measure** | A dynamic formula evaluated at query time based on user filter selections (e.g., `[Total Active Energy (kWh)] = SUM(Fact_EnergyConsumption[Active_Energy_kWh])`). |
