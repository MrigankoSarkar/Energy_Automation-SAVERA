# Chapter 4: Power BI & Microsoft Fabric Deployment

This chapter provides enterprise deployment procedures for integrating EnergyAutomation's dimensional data model into Microsoft Power BI Desktop, Power BI Service, and Microsoft Fabric Lakehouse environments.

---

## 1. Dimensional Model Artifacts Overview

EnergyAutomation automatically generates production-ready business intelligence artifacts in `data/powerbi_export/`:

| Artifact | File Name | Purpose |
| :--- | :--- | :--- |
| **Fact Table** | `Fact_EnergyConsumption.csv` | Granular daily meter readings, active/apparent energy, power factor, foreign keys. |
| **Date Dimension** | `Dim_Date.csv` | Calendar attributes: Day, Month, Year, Day of Week, Weekend Flag, Month Short. |
| **Meter Dimension** | `Dim_Meter.csv` | Physical meter ID, display name, category, rated power (kW), status. |
| **Area Dimension** | `Dim_Area.csv` | Shop floor zones: Area ID, Name, Zone Type, Baseline Target (kWh/day). |
| **Report Dimension** | `Dim_Report.csv` | Source PDF hash, ingestion timestamp, verification status, file size. |
| **DAX Measures** | `measures.dax` | Pre-engineered business formulas for active energy, distribution loss, and trends. |
| **REST Push Schema** | `dataset_schema.json` | JSON schema for direct push to Power BI Service via REST API. |
| **Report Template** | `powerbi_report_template.json` | Visual card, bar chart, and table specifications. |

---

## 2. Power BI Desktop Deployment (Star Schema Import)

### Step 1: Connect to Exported Dimension & Fact Files
1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Import each CSV file from `data/powerbi_export/`:
   - `Fact_EnergyConsumption.csv`
   - `Dim_Date.csv`
   - `Dim_Meter.csv`
   - `Dim_Area.csv`
   - `Dim_Report.csv`
4. In the Power Query editor, verify data types (integers for Keys, Decimals for kWh/kVAh, Dates for Date columns) and click **Close & Apply**.

### Step 2: Establish Model Relationships (Star Schema)
In Power BI's **Model View**, configure the one-to-many ($1 \to *$) single-direction relationships:
- `Dim_Date[Date_Key]` ($1$) $\to$ `Fact_EnergyConsumption[Date_Key]` ($*$)
- `Dim_Meter[Meter_Key]` ($1$) $\to$ `Fact_EnergyConsumption[Meter_Key]` ($*$)
- `Dim_Area[Area_Key]` ($1$) $\to$ `Fact_EnergyConsumption[Area_Key]` ($*$)
- `Dim_Report[Report_Key]` ($1$) $\to$ `Fact_EnergyConsumption[Report_Key]` ($*$)

```text
       +------------------+         +------------------+
       |     Dim_Date     |         |    Dim_Meter     |
       +------------------+         +------------------+
                 \                           /
                  \ (1)                 (1) /
                   \                       /
                    ▼                     ▼
               +-------------------------------+
               |    Fact_EnergyConsumption     |
               +-------------------------------+
                    ▲                     ▲
                   /                       \
                  / (1)                 (1) \
                 /                           \
       +------------------+         +------------------+
       |     Dim_Area     |         |    Dim_Report    |
       +------------------+         +------------------+
```

### Step 3: Import DAX Measures
Open `data/powerbi_export/measures.dax` in a text editor or **Tabular Editor 3**. Create a new calculation table `_Measures` and paste the pre-defined measures:
- `[Total Active Energy (kWh)]`
- `[Main Incomer Active Energy (kWh)]`
- `[Total Sub-Meters Active Energy (kWh)]`
- `[Distribution Loss (kWh)]`
- `[Distribution Loss %]`
- `[Average Power Factor]`

---

## 3. Power BI Service REST API Push Dataset Deployment

For real-time cloud analytics without maintaining an on-premises data gateway:

### Creating the Push Dataset via PowerShell
```powershell
$TenantId = "your-azure-tenant-id"
$ClientId = "your-app-client-id"
$ClientSecret = "your-app-client-secret"
$WorkspaceId = "your-powerbi-workspace-id"

# 1. Obtain Entra ID OAuth Access Token
$TokenBody = @{
    grant_type    = "client_credentials"
    client_id     = $ClientId
    client_secret = $ClientSecret
    resource      = "https://analysis.windows.net/powerbi/api"
}
$TokenResponse = Invoke-RestMethod -Uri "https://login.microsoftonline.com/$TenantId/oauth2/token" -Method Post -Body $TokenBody
$Headers = @{ Authorization = "Bearer $($TokenResponse.access_token)"; "Content-Type" = "application/json" }

# 2. Push Dataset Schema
$SchemaJson = Get-Content -Raw "data/powerbi_export/dataset_schema.json"
$Dataset = Invoke-RestMethod -Uri "https://api.powerbi.com/v1.0/myorg/groups/$WorkspaceId/datasets" -Method Post -Headers $Headers -Body $SchemaJson

Write-Host "Created Push Dataset ID: $($Dataset.id)"
```

Once created, store `$Dataset.id` in `config/settings.json` under `powerbi.dataset_id`. EnergyAutomation will automatically POST new rows to the cloud upon every successful report ingestion.

---

## 4. Microsoft Fabric & OneLake Integration

In organizations adopting **Microsoft Fabric**:
1. Mount the `data/powerbi_export/` directory as a Lakehouse Shortcut within your **Fabric Workspace**.
2. Create Delta Parquet tables pointing to `Fact_EnergyConsumption` and dimension tables.
3. Utilize **DirectLake** mode in Power BI semantic models for sub-second query performance across multi-year factory historical telemetry.
