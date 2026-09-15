# Chapter 1: System Requirements & Installation

This chapter outlines hardware specifications, supported operating systems, runtime prerequisites, and step-by-step installation instructions for enterprise deployment of EnergyAutomation.

---

## 1. System Requirements

### Recommended Hardware Specifications
| Component | Minimum Specification | Recommended Production Specification |
| :--- | :--- | :--- |
| **Processor (CPU)** | Intel Core i3 (4-core, 2.0 GHz) or AMD equivalent | Intel Core i5 / i7 (8-core, 3.0+ GHz) |
| **Memory (RAM)** | 4 GB | 8 GB or 16 GB |
| **Storage** | 2 GB available SSD space | 10 GB available NVMe SSD space (for 10+ years of backups & audit logs) |
| **Display** | 1366 × 768 resolution | 1920 × 1080 (Full HD) or higher |
| **Network** | 10 Mbps broadband internet | 100 Mbps stable corporate LAN / Ethernet |

### Operating System Compatibility
- **Supported Platforms**:
  - Windows 11 (64-bit, Professional / Enterprise / IoT Enterprise)
  - Windows 10 (64-bit, Version 21H2 or later)
  - Windows Server 2022 / Windows Server 2019 (Desktop Experience mode)
- **Architecture**: `x86_64` (AMD64).

---

## 2. Software Prerequisites

EnergyAutomation is built on Python 3.10+ (specifically validated through Python 3.14 on Windows) and PySide6 (Qt 6).

### 1. Python Environment
- Python 3.10 to 3.14 (64-bit).
- Ensure `pip` and virtual environment support (`venv`) are enabled.
- Ensure the option **"Add python.exe to PATH"** was selected during Python installation.

### 2. Microsoft Visual C++ Redistributable
- PySide6 and PyMuPDF (`fitz`) require the Microsoft Visual C++ 2015–2022 Redistributable (x64).
- Download from [Microsoft Support](https://aka.ms/vs/17/release/vc_redist.x64.exe) if not already installed.

---

## 3. Step-by-Step Installation

### Step 1: Clone or Copy the Repository
Place the application repository in a dedicated corporate deployment path, avoiding paths with special characters or excessive nesting:
```powershell
mkdir C:\Savera_EMS\
git clone https://github.com/MrigankoSarkar/Energy_Automation-SAVERA.git C:\Savera_EMS\EnergyAutomation
cd C:\Savera_EMS\EnergyAutomation
```

### Step 2: Create a Dedicated Virtual Environment
Using a project-isolated virtual environment prevents conflicts with system-wide Python libraries:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Production Dependencies
Install all required packages from `requirements.txt`:
```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 4: Verify Dependency Installation
Verify that PySide6, PyMuPDF, openpyxl, and SQLite can be imported cleanly:
```powershell
python -c "import PySide6, fitz, openpyxl, sqlite3; print('All core modules imported successfully.')"
```

---

## 4. Deploying Desktop Shortcuts & Auto-Start

### Creating a Desktop Shortcut with PowerShell
Run the following script to generate a Windows Desktop shortcut pointing to the virtual environment python interpreter:
```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\EnergyAutomation.lnk")
$Shortcut.TargetPath = "C:\Savera_EMS\EnergyAutomation\.venv\Scripts\pythonw.exe"
$Shortcut.Arguments = "run.py"
$Shortcut.WorkingDirectory = "C:\Savera_EMS\EnergyAutomation"
$Shortcut.IconLocation = "C:\Savera_EMS\EnergyAutomation\assets\app.ico"
$Shortcut.Description = "EnergyAutomation EMS Intelligence Platform"
$Shortcut.Save()
```
*(Note: Using `pythonw.exe` launches the application without displaying an unnecessary black console window).*

### Configuring Windows Auto-Start
To ensure EnergyAutomation starts automatically when the facility workstation logs in:
1. Press `Win + R`, type `shell:startup`, and press **Enter**.
2. Copy the `EnergyAutomation.lnk` shortcut into this Startup folder.
3. The application will start minimized to the Windows system tray and execute scheduled ingestion runs autonomously.
