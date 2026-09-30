from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from app.services.ai.prompt_manager import PromptManager


class GeminiService:
    """
    Gemini integration for EnergyAutomation.

    Gemini is used as an ANALYSIS and MONITORING layer.

    Important architectural rule:
        Gemini must not be the authoritative source for
        Excel writes, validation, dates, meter mapping, or
        numerical correctness.

    Deterministic application services remain authoritative.
    Gemini provides:
        - anomaly interpretation
        - operational observations
        - business-friendly explanations
        - monitoring summaries
        - recommendations
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enabled: bool = True,
        timeout: int = 60,
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_GEMINI_API_KEY")
        )

        self.model = (
            model
            or os.getenv("GEMINI_MODEL")
            or self.DEFAULT_MODEL
        )

        self.enabled = bool(enabled)
        self.timeout = int(timeout)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(
            self.enabled
            and self.api_key
        )

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "model": self.model,
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Verify Gemini API connectivity with a lightweight ping using official google-genai SDK
        and multi-model failover, with graceful fallback to REST.
        Measures roundtrip latency and validates API key credentials.
        """
        if not self.api_key:
            return {
                "success": False,
                "message": "API key is empty or not configured. Please enter your Gemini API key in Settings.",
                "latency_ms": 0,
            }

        import time

        candidate_models = [self.model]
        for fb in self.FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        # 1. Primary: Official google-genai SDK
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            for candidate in candidate_models:
                try:
                    t0 = time.perf_counter()
                    response = client.models.generate_content(
                        model=candidate,
                        contents="Health check ping. Respond with 'OK'.",
                    )
                    latency_ms = int((time.perf_counter() - t0) * 1000)
                    if response and hasattr(response, "text") and response.text:
                        self.model = candidate
                        return {
                            "success": True,
                            "message": f"Successfully connected via official google-genai SDK ({candidate}) in {latency_ms}ms.",
                            "latency_ms": latency_ms,
                            "model": candidate,
                            "sdk": "google-genai",
                        }
                except Exception:
                    continue
        except Exception:
            pass

        # 2. Fallback: Direct REST endpoint
        try:
            import requests

            last_err = ""
            for candidate in candidate_models:
                url = (
                    "https://generativelanguage.googleapis.com/"
                    "v1beta/models/"
                    f"{candidate}:generateContent"
                    f"?key={self.api_key}"
                )
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Health check ping. Respond with 'OK'."
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 10,
                    },
                }

                t0 = time.perf_counter()
                try:
                    resp = requests.post(url, json=payload, timeout=12)
                    latency_ms = int((time.perf_counter() - t0) * 1000)

                    if resp.status_code == 200:
                        self.model = candidate
                        return {
                            "success": True,
                            "message": f"Successfully connected to Google Gemini ({candidate}) in {latency_ms}ms.",
                            "latency_ms": latency_ms,
                            "model": candidate,
                            "sdk": "rest",
                        }
                    else:
                        err_msg = f"HTTP {resp.status_code}"
                        try:
                            err_json = resp.json()
                            if "error" in err_json:
                                err_msg = err_json["error"].get("message", err_msg)
                        except Exception:
                            pass
                        last_err = f"{candidate}: {err_msg}"
                except Exception as ex:
                    last_err = f"{candidate}: {ex}"

            return {
                "success": False,
                "message": f"Gemini API returned error: {last_err}",
                "latency_ms": 0,
                "model": self.model,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Connection failed: {str(exc)}",
                "latency_ms": 0,
            }

    # ------------------------------------------------------------------
    # Main analysis API
    # ------------------------------------------------------------------

    def analyze(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze EMS data.

        If Gemini is not configured, return a controlled result
        instead of breaking the automation pipeline.
        """

        if not self.enabled:
            return {
                "success": False,
                "enabled": False,
                "status": "disabled",
                "analysis": None,
            }

        if not self.api_key:
            return {
                "success": False,
                "enabled": True,
                "status": "not_configured",
                "analysis": None,
                "message": (
                    "Gemini API key is not configured. "
                    "Deterministic automation can continue."
                ),
            }

        prompt = self._build_analysis_prompt(
            data=data,
            context=context,
        )

        try:
            response = self._generate_content(
                prompt
            )

            return {
                "success": True,
                "enabled": True,
                "status": "completed",
                "model": self.model,
                "analysis": response,
            }

        except Exception as exc:
            return {
                "success": False,
                "enabled": True,
                "status": "error",
                "model": self.model,
                "analysis": None,
                "error": str(exc),
            }

    def analyze_report(
        self,
        report: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility API for report-level analysis.
        """
        return self.analyze(
            data=report,
            context=context,
        )

    def analyze_energy(
        self,
        readings: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility API for energy-reading analysis.
        """
        return self.analyze(
            data=readings,
            context=context,
        )

    def monitor(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Monitoring-oriented alias.
        """
        return self.analyze(
            data=data,
            context=context,
        )

    def summarize(
        self,
        data: Any,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Business-friendly summary API.
        """
        result = self.analyze(
            data=data,
            context=context,
        )

        if result.get("success"):
            result["summary"] = result.get(
                "analysis"
            )

        return result

    # ------------------------------------------------------------------
    # Natural-language Q&A
    # ------------------------------------------------------------------

    def ask(
        self,
        question: str,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Natural-language Q&A based strictly on verified application data.
        Never hallucinate numbers. If context_data is insufficient,
        explicitly returns 'Insufficient data available.'
        """
        if not question or not str(question).strip():
            return {
                "success": False,
                "answer": "Please provide a valid question.",
                "status": "empty_question",
            }

        ctx = dict(context_data or {})
        if not ctx:
            return {
                "success": True,
                "answer": (
                    "Insufficient data available.\n\n"
                    "💡 **How to guide and use the AI Insights system:**\n"
                    "• **Select File**: Ensure a valid Excel workbook is configured in Settings or Overview.\n"
                    "• **Run Automation**: Click '⚡ Run Automation Now' to pull the latest verified meter readings.\n"
                    "• **Configure API**: Check your Gemini API key in Settings → Advisory AI.\n\n"
                    "**Suggested Prompts to Ask:**\n"
                    "1. *What is the total energy consumption yesterday?*\n"
                    "2. *Which meters consumed the most energy?*\n"
                    "3. *Are there any missing report dates in the last 30 days?*\n"
                    "4. *Check for anomalies, zero readings, or negative values.*"
                ),
                "status": "insufficient_data",
                "suggestions": [
                    "What is the total energy consumption yesterday?",
                    "Which meters consumed the most energy?",
                    "Are there any missing report dates?",
                    "Check for anomalies across all meters",
                ],
            }

        # Enrich context fields if nested in latest_report/readings
        if "latest_report" in ctx and isinstance(ctx["latest_report"], dict):
            lr = ctx["latest_report"]
            if "total_energy" not in ctx and "total_energy" in lr:
                ctx["total_energy"] = lr["total_energy"]
            if "total" not in ctx and "total_energy" in lr:
                ctx["total"] = lr["total_energy"]
            if "report_date" not in ctx and "report_date" in lr:
                ctx["report_date"] = lr["report_date"]

        if "readings" in ctx and isinstance(ctx["readings"], list):
            if "meters" not in ctx:
                ctx["meters"] = ctx["readings"]
            if "top_meters" not in ctx:
                valid_m = [
                    m for m in ctx["readings"]
                    if isinstance(m, dict) and (m.get("value") is not None or m.get("active_energy") is not None)
                ]
                ctx["top_meters"] = sorted(
                    valid_m,
                    key=lambda x: float(x.get("value") if x.get("value") is not None else x.get("active_energy", 0)),
                    reverse=True,
                )

        if not self.enabled or not self.api_key:
            return self._deterministic_fallback_qa(question, ctx)

        prompt = PromptManager.build_qa_prompt(question=question, context_data=ctx)
        try:
            answer = self._generate_content(prompt)
            return {
                "success": True,
                "status": "completed",
                "answer": answer,
                "model": self.model,
            }
        except Exception as exc:
            fb = self._deterministic_fallback_qa(question, ctx)
            if fb.get("status") != "insufficient_data":
                fb["note"] = f"Cloud AI unavailable ({exc}); served via verified deterministic engine."
                return fb
            return {
                "success": False,
                "status": "error",
                "answer": f"AI service error: {exc}",
                "error": str(exc),
            }

    def _deterministic_fallback_qa(
        self,
        question: str,
        context_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Provides guaranteed accurate deterministic answers even when Gemini API is offline.
        """
        q_lower = question.lower()
        if "top" in q_lower or "highest" in q_lower or "most" in q_lower:
            meters = context_data.get("meters") or context_data.get("top_meters") or []
            if meters:
                valid_m = [
                    m for m in meters
                    if m.get("value") is not None or m.get("active_energy") is not None
                ]
                top_m = sorted(
                    valid_m,
                    key=lambda x: float(x.get("value") if x.get("value") is not None else x.get("active_energy", 0)),
                    reverse=True,
                )[:5]
                lines = [
                    f"- {m.get('meter_name')}: {m.get('value') or m.get('active_energy')} kWh"
                    for m in top_m
                ]
                return {
                    "success": True,
                    "status": "deterministic_fallback",
                    "answer": "Top energy consuming meters:\n" + "\n".join(lines),
                }

        if "total" in q_lower or "yesterday" in q_lower or "consumption" in q_lower:
            total = context_data.get("total_energy") or context_data.get("total")
            if total is not None:
                return {
                    "success": True,
                    "status": "deterministic_fallback",
                    "answer": f"Total energy consumption recorded is {total} kWh.",
                }

        if "missing" in q_lower or "gap" in q_lower:
            missing = context_data.get("missing_dates") or []
            if missing:
                return {
                    "success": True,
                    "status": "deterministic_fallback",
                    "answer": f"Detected missing report dates: {', '.join(missing)}.",
                }
            return {
                "success": True,
                "status": "deterministic_fallback",
                "answer": "No missing report dates detected.",
            }

        return {
            "success": True,
            "status": "insufficient_data",
            "answer": (
                "Insufficient data available.\n\n"
                "💡 **Organized Suggestions to Guide Your Analysis:**\n"
                "• Ask about consumption: *'What was total energy consumption yesterday?'*\n"
                "• Ask about high loads: *'Which meter consumed the most energy?'*\n"
                "• Check data completeness: *'Are there any missing dates or gaps?'*\n"
                "• Anomaly detection: *'Run local anomaly check on all meters.'*"
            ),
            "suggestions": [
                "What is the total energy consumption yesterday?",
                "Which meter consumed the most energy?",
                "Are there any missing dates?",
                "Show anomaly check results",
            ],
        }

    def local_anomaly_check(
        self,
        readings: Any,
    ) -> Dict[str, Any]:
        """
        Lightweight deterministic anomaly detection.

        This does not call Gemini and is safe for unattended
        operation.

        It identifies:
        - negative energy
        - extremely large values
        - missing values
        - N/A values
        """

        normalized = self._normalize_readings(
            readings
        )

        anomalies = []
        valid_count = 0
        na_count = 0

        for item in normalized:
            meter = item["meter_name"]
            value = item["value"]
            status = item["status"].upper()

            if (
                status in {
                    "N/A",
                    "NA",
                    "MISSING",
                    "NOT_AVAILABLE",
                }
                or value is None
            ):
                na_count += 1
                continue

            numeric = self._to_float(value)

            if numeric is None:
                anomalies.append({
                    "meter": meter,
                    "type": "invalid_numeric_value",
                    "value": value,
                })
                continue

            valid_count += 1

            if numeric < 0:
                anomalies.append({
                    "meter": meter,
                    "type": "negative_energy",
                    "value": numeric,
                })

            if numeric > 100_000_000:
                anomalies.append({
                    "meter": meter,
                    "type": "extreme_energy_value",
                    "value": numeric,
                })

        return {
            "success": True,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "valid_count": valid_count,
            "na_count": na_count,
        }

    # ------------------------------------------------------------------
    # Gemini REST integration
    # ------------------------------------------------------------------

    def _generate_content(
        self,
        prompt: str,
    ) -> str:
        """
        Generate content using the official google-genai SDK, with automatic REST fallback
        and multi-model failover.
        """
        if not self.api_key:
            raise RuntimeError("Gemini API key is not configured.")

        candidate_models = [self.model]
        for fb in self.FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        # 1. Primary: Official google-genai SDK
        sdk_errors = []
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            for candidate in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                    )
                    if response and hasattr(response, "text") and response.text:
                        self.model = candidate
                        return response.text.strip()
                except Exception as ex:
                    sdk_errors.append(f"{candidate}: {ex}")
        except Exception as e:
            sdk_errors.append(f"SDK init: {e}")

        # 2. Fallback: Direct REST endpoint
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError(
                "The 'requests' package is required for Gemini integration."
            ) from exc

        last_error = None
        for candidate in candidate_models:
            url = (
                "https://generativelanguage.googleapis.com/"
                "v1beta/models/"
                f"{candidate}:generateContent"
                f"?key={self.api_key}"
            )

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                },
            }

            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    self.model = candidate
                    body = response.json()
                    return self._extract_text(body)
                else:
                    err_msg = f"HTTP {response.status_code}"
                    try:
                        err_json = response.json()
                        if "error" in err_json:
                            err_msg = err_json["error"].get("message", err_msg)
                    except Exception:
                        pass
                    last_error = f"{candidate}: {err_msg}"
            except Exception as exc:
                last_error = f"{candidate}: {exc}"

        raise RuntimeError(
            f"All Gemini models failed across google-genai SDK and REST. "
            f"SDK: {'; '.join(sdk_errors[-2:]) if sdk_errors else 'N/A'} | REST: {last_error}"
        )

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_analysis_prompt(
        self,
        data: Any,
        context: Optional[str],
    ) -> str:

        serialized = self._safe_json(
            data
        )

        context_text = (
            context
            if context
            else "No additional context provided."
        )

        return f"""
You are the monitoring and business-analysis assistant
for an industrial Energy Management System automation.

Analyze the supplied EMS information.

Your responsibilities:
1. Identify meaningful energy-consumption anomalies.
2. Identify missing, incomplete, or suspicious readings.
3. Explain important observations in simple business language.
4. Highlight meters that may require attention.
5. Distinguish facts from possible explanations.
6. Never invent measurements.
7. Never replace deterministic validation.
8. Never instruct the application to overwrite Excel data
   unless the deterministic validation layer has already
   accepted that data.

Context:
{context_text}

EMS data:
{serialized}

Return a concise structured analysis containing:
- Overall status
- Important observations
- Possible anomalies
- Meters requiring attention
- Business impact
- Recommended follow-up actions

If the data does not support a conclusion, explicitly say
that there is insufficient evidence.
""".strip()

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(
        response: Dict[str, Any],
    ) -> str:

        candidates = response.get(
            "candidates"
        )

        if not candidates:
            raise RuntimeError(
                "Gemini returned no candidates."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        texts = []

        for part in parts:
            text = part.get("text")

            if text:
                texts.append(
                    str(text)
                )

        if not texts:
            raise RuntimeError(
                "Gemini returned no text content."
            )

        return "\n".join(texts).strip()

    # ------------------------------------------------------------------
    # Data normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_readings(
        readings: Any,
    ):

        if readings is None:
            return []

        if isinstance(readings, dict):

            if isinstance(
                readings.get("readings"),
                (list, tuple),
            ):
                readings = readings[
                    "readings"
                ]

            elif "meter_name" in readings:
                readings = [readings]

            else:
                converted = []

                for meter, value in readings.items():

                    if isinstance(
                        value,
                        dict,
                    ):
                        item = dict(value)
                        item.setdefault(
                            "meter_name",
                            meter,
                        )
                    else:
                        item = {
                            "meter_name": meter,
                            "value": value,
                        }

                    converted.append(item)

                readings = converted

        normalized = []

        for item in readings:

            if not isinstance(
                item,
                dict,
            ):
                continue

            meter = (
                item.get("meter_name")
                or item.get("meter")
                or item.get("name")
                or ""
            )

            value = (
                item.get("active_energy")
                if "active_energy" in item
                else item.get("value")
            )

            status = str(
                item.get("status")
                or ""
            )

            normalized.append({
                "meter_name": str(
                    meter
                ).strip(),
                "value": value,
                "unit": item.get(
                    "unit",
                    "kWh",
                ),
                "status": status,
            })

        return normalized

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_json(
        data: Any,
    ) -> str:

        try:
            return json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(data)

    @staticmethod
    def _to_float(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        text = str(
            value
        ).strip()

        if not text:
            return None

        if text.upper() in {
            "N/A",
            "NA",
            "NONE",
            "NULL",
            "-",
        }:
            return None

        text = (
            text.replace(
                "kWh",
                "",
            )
            .replace(
                "KWH",
                "",
            )
            .replace(
                "kwh",
                "",
            )
            .replace(
                ",",
                "",
            )
            .strip()
        )

        try:
            return float(text)
        except (
            TypeError,
            ValueError,
        ):
            return None