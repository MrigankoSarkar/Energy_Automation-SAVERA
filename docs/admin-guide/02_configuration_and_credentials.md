# Chapter 2: Configuration & Credentials Management

This chapter covers the configuration parameters, authentication schemes, credential management, and secret security within EnergyAutomation.

---

## 1. Configuration Architecture

EnergyAutomation uses a layered configuration system designed for enterprise operational stability:
1. **Default Settings**: Embedded application defaults defined in `app/config/settings.py`.
2. **Configuration File**: Persistent JSON settings stored in `config/settings.json`.
3. **Environment Variables**: Operating system environment variables that take precedence over JSON files for automated containerized or CI/CD deployments.

### Key Configuration Keys
```json
{
  "excel": {
    "workbook_path": "Test_BI_Analysis_Report_2026.xlsx",
    "sheet_name_pattern": "{MONTH_SHORT} - {YEAR}",
    "auto_backup": true,
    "max_backups": 30
  },
  "gmail": {
    "enabled": false,
    "credentials_path": "credentials.json",
    "token_path": "token.pickle",
    "sender_filter": "ems-reports@savera-ms.com",
    "subject_query": "NBSense EMS Monitoring Report"
  },
  "scheduler": {
    "enabled": true,
    "run_time": "06:00",
    "poll_interval_minutes": 15,
    "run_on_startup": false
  },
  "powerbi": {
    "enabled": false,
    "client_id": "",
    "client_secret": "",
    "tenant_id": "",
    "workspace_id": "",
    "dataset_id": ""
  },
  "ai": {
    "enabled": false,
    "provider": "google_gemini",
    "model": "gemini-2.5-flash",
    "api_key": ""
  }
}
```

---

## 2. Gmail Integration Setup (Google Cloud Console)

EnergyAutomation can download daily NBSense PDF reports automatically from a designated operational Gmail inbox.

### Step-by-Step OAuth 2.0 Credentials Setup
1. Log into the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project named `EnergyAutomation-EMS`.
3. Under **APIs & Services**, enable the **Gmail API**.
4. Go to **OAuth consent screen**:
   - Choose **Internal** (for Google Workspace organizations) or **External** (with test users added).
   - Fill in App Name (`EnergyAutomation`) and User Support Email.
   - Add the Gmail read-only scope: `https://www.googleapis.com/auth/gmail.readonly`.
5. Go to **Credentials** -> **Create Credentials** -> **OAuth Client ID**:
   - Application type: **Desktop app**.
   - Name: `EnergyAutomation-DesktopClient`.
   - Click **Create**.
6. Download the JSON file and rename it to `credentials.json`.
7. Place `credentials.json` into the root application directory: `C:\Savera_EMS\EnergyAutomation\credentials.json`.
8. On first run, click **Test Gmail Connection** in Settings. A browser window will open asking you to log into the Gmail account and grant read-only permissions.
9. Upon approval, EnergyAutomation automatically writes `token.pickle` to the project root. Future scheduled runs will refresh access tokens automatically without user intervention.

---

## 3. Google Gemini AI API Configuration

To enable the conversational AI Assistant:
1. Navigate to [Google AI Studio](https://aistudio.google.com/).
2. Create an API Key under your enterprise Google account.
3. You can configure the API key in two ways:
   - **GUI Method**: Open EnergyAutomation -> **Settings** -> paste into **Gemini API Key** -> click **Save**.
   - **Environment Variable Method**: Set the system environment variable:
     ```powershell
     [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'AIzaSyYourSecretKeyHere...', [System.EnvironmentVariableTarget]::Machine)
     ```
4. In production environments, the system masks the API key in UI logs (`AIzaSy****...`).

---

## 4. Microsoft Power BI Service Principal Configuration

To push live energy data directly to Power BI cloud workspaces:
1. Log into the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Microsoft Entra ID (Azure AD)** -> **App registrations** -> **New registration**.
   - Name: `EnergyAutomation-PowerBI-ServicePrincipal`.
3. Note the **Application (client) ID** and **Directory (tenant) ID**.
4. Under **Certificates & secrets**, generate a **New client secret** and securely store the value.
5. In the [Power BI Admin Portal](https://app.powerbi.com/):
   - Under **Tenant settings** -> **Developer settings**, enable **"Allow service principals to use Power BI APIs"**.
   - Add the security group containing your App Registration.
6. In your target Power BI Workspace:
   - Go to **Workspace Access** and add the App Registration as a **Contributor** or **Admin**.
7. Enter these credentials into EnergyAutomation's **Settings** view or set the environment variables:
   - `POWERBI_CLIENT_ID`
   - `POWERBI_CLIENT_SECRET`
   - `POWERBI_TENANT_ID`
   - `POWERBI_WORKSPACE_ID`

---

## 5. Security & Permission Hardening

1. **File System Permissions**: Ensure the `credentials.json` and `token.pickle` files are only readable by the Windows service user executing the application.
   ```powershell
   icacls "C:\Savera_EMS\EnergyAutomation\credentials.json" /inheritance:r /grant:r "Administrators:(F)" "$env:USERNAME:(R,W)"
   icacls "C:\Savera_EMS\EnergyAutomation\token.pickle" /inheritance:r /grant:r "Administrators:(F)" "$env:USERNAME:(R,W)"
   ```
2. **Log Sanitization**: The application's logging pipeline automatically strips sensitive tokens, client secrets, and passwords before writing to `logs/audit.log` or displaying output in GUI widgets.
