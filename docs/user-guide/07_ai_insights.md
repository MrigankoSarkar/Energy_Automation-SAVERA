# Chapter 7: AI Insights & Engineering Q&A

The **AI Energy Assistant** in EnergyAutomation is an intelligent advisory tool powered by Google Gemini (e.g. Gemini 2.5 Flash / Pro). It provides plant managers, electrical engineers, and operational teams with conversational access to facility energy metrics, anomaly explanations, and actionable energy conservation measures (ECMs).

---

## 1. Architectural Safeguards & Role Definition

EnergyAutomation adheres to a strict architectural rule regarding artificial intelligence:

> [!IMPORTANT]
> **Deterministic Single Source of Truth**
> The mathematical parsing, SQLite persistence, and Excel automation pipelines are 100% deterministic and never depend on AI. Gemini AI is strictly a **read-only advisory layer**. It cannot modify Excel spreadsheets, write to SQLite databases, or alter incoming NBSense meter values.

### The Guardrail Principles
1. **Zero Hallucination Grounding**: The AI assistant receives verified, pre-aggregated facility facts (date, total active energy, top consuming meters, baseline comparisons) injected directly into its system prompt context.
2. **Explicit Fallback Mode**: If the Google Gemini API key is not configured, or if network connectivity is unavailable, the AI Assistant does not crash. It switches to an internal, deterministic rule-based assistant that can answer common analytical questions (e.g., total energy, top 5 meters, power factor status).
3. **No External Data Leakage**: Only aggregated meter names and energy metrics for the inspected dates are transmitted to the LLM. No confidential proprietary formulas or external client identifiers are shared.

---

## 2. Using the AI Insights View

To access the AI Assistant:
1. Open EnergyAutomation.
2. In the navigation sidebar, click **AI Insights** (or press `Ctrl+7`).

### User Interface Overview
The AI Insights screen features:
- **Conversation Stream**: A chronological chat transcript displaying user questions and structured AI responses.
- **Prompt Preset Chips**: One-click quick query buttons for standard operational questions:
  - *"Summarize today's energy usage"*
  - *"Which meters exceeded normal thresholds?"*
  - *"Compare Main Incomer vs sub-meter sums"*
  - *"Recommend peak load shaving actions"*
- **Query Input Box & Send Button**: A text field allowing arbitrary technical and managerial questions.
- **Model / Status Indicator**: Displays whether the assistant is running via `Gemini 2.5 Flash (Cloud)` or `Deterministic Fallback (Local)`.

---

## 3. Sample Questions & Expected Answers

### Query: *"What was our total energy consumption for the latest report?"*
- **Assistant Response**:
  > Based on the verified NBSense report for **15-02-2026**, the total facility active energy recorded was **9,206.83 kWh**. The primary consumer was **PDB-1 (Shop Floor Main)** accounting for 28.4% of total facility consumption.

### Query: *"Which 5 meters consumed the most energy?"*
- **Assistant Response**:
  > The top 5 energy consumers on 15-02-2026 were:
  > 1. **PDB-1 (Shop Floor Main)**: 2,618.40 kWh
  > 2. **PDB-2 (Machining Center)**: 1,842.10 kWh
  > 3. **Compressor-1**: 1,230.50 kWh
  > 4. **Furnace-B**: 985.20 kWh
  > 5. **HVAC Chiller-1**: 760.30 kWh
  >
  > *Observation*: Compressor-1 baseline consumption increased by 14% compared to the 30-day average. Recommend inspecting pneumatic line filters and checking for compressed air leaks during non-operational hours.

### Query: *"Why is there a discrepancy between Main Incomer and Sub-meters?"*
- **Assistant Response**:
  > Active Energy Incomer: **9,206.83 kWh**.  
  > Sum of Downstream Sub-meters: **8,842.15 kWh**.  
  > **Unmetered Delta / Distribution Loss**: **364.68 kWh (3.96%)**.  
  > A distribution loss under 5% is standard for industrial switchgear and transformer impedance. If this delta exceeds 7%, inspect intermediate sub-distribution panels (Lighting DB, Utility Shed) for unmonitored tap-offs.

---

## 4. Configuring Gemini AI in Settings

To enable cloud-powered Gemini reasoning:
1. Navigate to **Settings** (`Ctrl+,`).
2. Locate the **AI & Intelligence Configuration** section.
3. Check **Enable Gemini AI Assistant**.
4. Enter your **Google Gemini API Key** (obtained from Google AI Studio).
5. Select your preferred model tier:
   - `gemini-2.5-flash`: Recommended. Fast response times (< 1.5s), cost-efficient, and optimized for data summarization.
   - `gemini-2.5-pro`: Recommended for complex engineering root-cause analysis and multi-day trend synthesis.
6. Click **Test AI Connection**. The system tests the key against a minimal prompt. Upon success, click **Save Settings**.

---

## 5. Offline / Local Fallback Behavior

When offline or operating without an API key:
- The UI status badge updates to: `AI Engine: Deterministic Fallback (Offline Mode)`.
- Pre-programmed analytical routines parse queries for keywords such as `"total"`, `"top"`, `"meters"`, `"incomer"`, and `"summary"`.
- Instant mathematical responses are generated directly from the local SQLite database without sending network packets.
