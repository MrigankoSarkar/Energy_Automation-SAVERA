"""
Prompt Manager for Gemini AI Service.

Constructs safe, context-rich prompts for anomaly interpretation,
report understanding, and natural-language Q&A based on verified application data.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


class PromptManager:
    """Constructs deterministic, hallucination-resistant prompts for Gemini."""

    @staticmethod
    def build_qa_prompt(question: str, context_data: Dict[str, Any]) -> str:
        """
        Build a prompt for natural-language Q&A using strictly verified application data.
        """
        serialized_context = json.dumps(context_data, indent=2, default=str)
        return f"""
You are the AI Energy Analyst and Monitoring Assistant for EnergyAutomation,
an enterprise industrial Energy Management System (EMS).

A plant engineer or executive asks:
"{question}"

You MUST answer using ONLY the verified application data provided below.

CRITICAL RULES:
1. NEVER invent, assume, or hallucinate numbers or events.
2. If the answer cannot be determined from the provided data, respond EXACTLY:
   "Insufficient data available."
3. Distinguish clearly between facts directly observed in data and potential operational hypotheses.
4. Keep the response concise, executive-friendly, and actionable.
5. You have NO permission or capability to modify Excel, database, or settings.

VERIFIED APPLICATION DATA:
{serialized_context}

Answer:
""".strip()

    @staticmethod
    def build_anomaly_prompt(
        anomalies: list[dict],
        meter_data: list[dict],
        context: Optional[str] = None,
    ) -> str:
        """
        Build a prompt to interpret energy consumption anomalies.
        """
        anomalies_json = json.dumps(anomalies, indent=2, default=str)
        meters_json = json.dumps(meter_data, indent=2, default=str)
        extra_ctx = context or "Normal daily manufacturing operations."

        return f"""
You are an expert industrial energy management analyst.
Explain the following detected energy consumption anomalies in clear business language.

Context:
{extra_ctx}

Detected Anomalies:
{anomalies_json}

Meter Readings:
{meters_json}

Provide:
1. Summary of significant spikes or drops.
2. Potential plant operational causes (e.g. production shifts, compressor leaks, maintenance, heating/cooling demand).
3. Recommended diagnostic steps for engineering staff.
4. If evidence is lacking for an anomaly, state "Insufficient data to determine cause."
""".strip()

    @staticmethod
    def build_structure_analysis_prompt(
        pdf_metadata: dict,
        extracted_meters: list[dict],
    ) -> str:
        """
        Build a prompt to classify unusual report structures or ambiguous meter names.
        """
        meta_json = json.dumps(pdf_metadata, indent=2, default=str)
        meters_json = json.dumps(extracted_meters, indent=2, default=str)

        return f"""
You are an intelligent document layout assistant.
Review the extracted EMS PDF structure for potential irregularities.

Metadata:
{meta_json}

Extracted Meters:
{meters_json}

Identify:
1. Any ambiguous or split meter names that might be continuation lines.
2. Unusual layout changes compared to standard NBSense daily reports.
3. Suggest canonical aliases if any meter name is slightly deformed.
""".strip()
