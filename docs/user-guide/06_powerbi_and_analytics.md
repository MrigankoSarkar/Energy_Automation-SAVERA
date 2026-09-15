# EnergyAutomation — User Guide: Power BI & Analytics

## 1. Power BI Analytical Model
EnergyAutomation provides automated business intelligence capabilities designed to feed corporate Microsoft Power BI and Fabric dashboards.

The application generates a **star-schema dimensional model**:
```
             Dim_Date
                |
                v
Dim_Meter -> Fact_EnergyConsumption <- Dim_Area
                ^
                |
            Dim_Report
```

---

## 2. Generated Star-Schema Files
Whenever reports are processed, or upon clicking **Export Star-Schema & DAX Files**, the following files are refreshed in `data/powerbi/`:
1. `Fact_EnergyConsumption.csv`: Granular daily meter readings with DateKey, MeterKey, AreaKey, ActiveEnergy_kWh, IsWeekend, and Status.
2. `Dim_Date.csv`: Contiguous calendar dimension covering past 90 days to +30 days with Year, Month, Day, DayOfWeek, and IsWeekend flags.
3. `Dim_Meter.csv`: Meter dimension with rated capacity in kW and nominal baseline in kWh.
4. `Dim_Area.csv`: Plant production areas (Plating, Coating, Fabrication, Compressors, Water Treatment, Substation).
5. `Dim_Report.csv`: High-level daily report audit headers with SHA-256 hashes and mapped meter counts.
6. `measures.dax`: Complete set of DAX formulas ready to copy into Power BI Desktop.
7. `dataset_schema.json`: Push Dataset definition compatible with Power BI REST API.
8. `powerbi_report_template.json`: Layout definitions for Executive, Engineering, and Data Quality views.

---

## 3. How to Connect Power BI Desktop
1. Open Power BI Desktop.
2. Click **Get Data** → **Folder** or **CSV/Text**.
3. Select the `data/powerbi/` directory from your EnergyAutomation installation.
4. Import `Fact_EnergyConsumption.csv`, `Dim_Date.csv`, `Dim_Meter.csv`, `Dim_Area.csv`, and `Dim_Report.csv`.
5. In the Model view, verify the 1-to-many relationships:
   - `Dim_Date[DateKey]` → `Fact_EnergyConsumption[DateKey]`
   - `Dim_Meter[MeterKey]` → `Fact_EnergyConsumption[MeterKey]`
   - `Dim_Area[AreaKey]` → `Fact_EnergyConsumption[AreaKey]`
6. Copy the DAX measures from `data/powerbi/measures.dax` into your model.
