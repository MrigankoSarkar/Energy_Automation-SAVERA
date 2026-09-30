# EnergyAutomation — Desktop UI/UX Design System Guide

## 1. Design Philosophy

The EnergyAutomation desktop interface is built using **PySide6** and **QFluentWidgets**, adhering strictly to the **Windows 11 Fluent Design System**. 

The interface was designed with four primary tenets:
1. **Zero Fake Telemetry**: The UI never manufactures placeholder numbers (`2500 kWh`, `0.0`, fake dates). Every KPI, chart, and badge is either dynamically parsed from the active production Excel workbook / SQLite database or explicitly marked as `NOT ACTIVE` / `NO DATA AVAILABLE`.
2. **Unified Enterprise Workflow**: Streamlined navigation structure focusing on operational monitoring, historical gap recovery, Gemini AI advisory, and Plotly Dash BI integration.
3. **Strict Color Contrast Rules**: Dark-on-dark or light-on-light text and background collisions are strictly forbidden. All foreground, border, and background tokens are defined with verified WCAG AA contrast ratios.
4. **Permanent Light-Themed Onboarding**: The Guided Tour and First-Run Setup Wizard always render in a clean, high-contrast Light Theme regardless of system or dark theme settings, preventing illegible dialog text.

---

## 2. Design Tokens (`ui/design_system/tokens.py`)

All layout elements, backgrounds, borders, and typography utilize centralized design tokens.

### 2.1 Theme Colors

| Token Name | Light Theme | Dark Theme | Purpose |
| :--- | :--- | :--- | :--- |
| `bg_canvas` | `#f3f4f6` | `#202020` | Application window background |
| `bg_surface` | `#ffffff` | `#2d2d2d` | Card and panel surfaces |
| `bg_subtle` | `#f8fafc` | `#262626` | Secondary panels, grouped controls |
| `fg_primary` | `#0f172a` | `#ffffff` | Primary headings and prominent values |
| `fg_secondary` | `#475569` | `#d1d5db` | Body text and descriptions |
| `fg_muted` | `#64748b` | `#9ca3af` | Secondary labels and timestamps |
| `border_card` | `#e2e8f0` | `#3d3d3d` | Card borders |
| `accent` | `#0078d4` | `#60cdff` | Primary action buttons and focus rings |
| `status_success` | `#16a34a` | `#4ade80` | Operational, validated, normal status |
| `status_warning` | `#d97706` | `#fbbf24` | Gaps detected, token expiring, unpolled |
| `status_danger` | `#dc2626` | `#f87171` | Pipeline errors, file locks, bounds violated |

---

## 3. Typography Hierarchy (`ui/design_system/typography.py`)

Typography is based on the Windows 11 default font family: **Segoe UI Variable**, **Segoe UI**, or system fallbacks.

| Style Role | Font Family | Size | Weight | Line Height |
| :--- | :--- | :--- | :--- | :--- |
| **Title / Hero** | Segoe UI Variable Display | 20pt (28px) | 700 (Bold) | 1.2 |
| **Section Header**| Segoe UI Variable Display | 13pt (18px) | 600 (SemiBold)| 1.3 |
| **KPI Value** | Segoe UI Variable Display | 20pt (28px) | 700 (Bold) | 1.0 |
| **Body Primary** | Segoe UI Variable Text | 10pt (14px) | 400 (Regular) | 1.4 |
| **Body Secondary**| Segoe UI Variable Text | 9.5pt (13px) | 400 (Regular) | 1.4 |
| **Caption / Meta**| Segoe UI Variable Small | 8.5pt (11px) | 500 (Medium) | 1.2 |

---

## 4. Centralized Notification System (`ui/notification_service.py`)

Desktop notifications are handled by `UINotificationService`:
- **Toast Notifications**: Built with `qfluentwidgets.InfoBar` (Success, Info, Warning, Error) appearing non-intrusively at the top-right of the window.
- **Friendly Technical Dialogs**: When an exception occurs (e.g. `PermissionError: WinError 32` or OAuth token expiry), the user is presented with a plain-language explanation, immediate recommended actions, and a collapsible technical stack trace section for IT support.
