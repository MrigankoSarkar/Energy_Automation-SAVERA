from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class ReportRepository:

    def __init__(self, database):
        self.database = database

    def save_report(
        self,
        message_id: str,
        report_date: str,
        status: str,
        pdf_path: str = "",
        attachment_name: str = "",
        attachment_hash: str = "",
        received_date: str = "",
        processing_date: str = "",
        meter_count: int = 0,
        mapped_meter_count: int = 0,
        missing_meter_count: int = 0,
        total_energy: float = 0.0,
        validation_status: str = "VALID",
        excel_status: str = "UPDATED",
        powerbi_status: str = "DISABLED",
        ai_status: str = "NORMAL",
        retry_count: int = 0,
        error_message: str = "",
    ):
        existing = self.database.fetch_all(
            "SELECT id FROM reports WHERE message_id = ? AND report_date = ?",
            (str(message_id), str(report_date)),
        )
        if existing:
            report_id = existing[0]["id"]
            self.database.execute(
                """
                UPDATE reports SET
                    status = ?,
                    pdf_path = ?,
                    attachment_name = ?,
                    attachment_hash = ?,
                    received_date = ?,
                    processing_date = ?,
                    meter_count = ?,
                    mapped_meter_count = ?,
                    missing_meter_count = ?,
                    total_energy = ?,
                    validation_status = ?,
                    excel_status = ?,
                    powerbi_status = ?,
                    ai_status = ?,
                    retry_count = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    status,
                    pdf_path,
                    attachment_name,
                    attachment_hash,
                    received_date,
                    processing_date,
                    meter_count,
                    mapped_meter_count,
                    missing_meter_count,
                    total_energy,
                    validation_status,
                    excel_status,
                    powerbi_status,
                    ai_status,
                    retry_count,
                    error_message,
                    report_id,
                ),
            )
            return report_id

        cursor = self.database.execute(
            """
            INSERT INTO reports
            (
                message_id,
                report_date,
                status,
                pdf_path,
                attachment_name,
                attachment_hash,
                received_date,
                processing_date,
                meter_count,
                mapped_meter_count,
                missing_meter_count,
                total_energy,
                validation_status,
                excel_status,
                powerbi_status,
                ai_status,
                retry_count,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                report_date,
                status,
                pdf_path,
                attachment_name,
                attachment_hash,
                received_date,
                processing_date,
                meter_count,
                mapped_meter_count,
                missing_meter_count,
                total_energy,
                validation_status,
                excel_status,
                powerbi_status,
                ai_status,
                retry_count,
                error_message,
            ),
        )
        return cursor.lastrowid

    def save_reading(
        self,
        report_id: int,
        meter_name: str,
        active_energy,
        unit: str,
        status: str,
    ):
        self.database.execute(
            """
            INSERT INTO meter_readings
            (
                report_id,
                meter_name,
                active_energy,
                unit,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                report_id,
                meter_name,
                active_energy,
                unit,
                status,
            ),
        )

    def record_processed_report(
        self,
        report: Dict[str, Any],
        parsed: Dict[str, Any],
        excel_result: Any = None,
        validation_result: Any = None,
        powerbi_result: Any = None,
        ai_result: Any = None,
        error: Any = None,
    ) -> int | None:
        """
        Record a fully processed EMS report with complete audit trail and meter readings.
        """
        import hashlib
        from datetime import datetime

        message_id = (
            report.get("message_id")
            or report.get("id")
            or parsed.get("source_message_id")
            or f"report_{parsed.get('report_date_iso', 'unknown')}"
        )

        report_date = (
            parsed.get("report_date_iso")
            or str(parsed.get("report_date", ""))
        )

        pdf_path = (
            report.get("pdf_path")
            or report.get("path")
            or parsed.get("source_file")
            or ""
        )

        attachment_name = Path(pdf_path).name if pdf_path else ""
        attachment_hash = ""
        if pdf_path and Path(pdf_path).exists():
            try:
                with open(pdf_path, "rb") as f:
                    attachment_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            except Exception:
                pass

        success = (
            getattr(excel_result, "success", False)
            if excel_result is not None
            else (error is None)
        )
        status = "COMPLETED" if success else "FAILED"

        readings = parsed.get("readings", [])
        meter_count = len(readings)

        mapped_count = getattr(excel_result, "updated_cells", [])
        mapped_meter_count = max(0, len(mapped_count) - 1) if mapped_count else meter_count
        missing_meter_count = max(0, meter_count - mapped_meter_count)

        total_energy = float(getattr(excel_result, "total_value", 0.0) or 0.0)
        if total_energy == 0.0 and readings:
            total_energy = sum(
                float(r.get("value") or r.get("active_energy") or 0.0)
                for r in readings
                if str(r.get("status", "")).upper() not in {"N/A", "NA"}
                and (r.get("value") is not None or r.get("active_energy") is not None)
            )

        val_status = "VALID" if (validation_result is None or validation_result.get("valid", True)) else "INVALID"
        exc_status = "UPDATED" if success else "FAILED"
        pbi_status = "SYNCED" if (powerbi_result and powerbi_result.get("success")) else "DISABLED"
        ai_stat = "NORMAL" if (ai_result is None or ai_result.get("status") != "attention_required") else "ANOMALY"

        err_msg = str(error) if error else (getattr(excel_result, "message", "") or "")

        report_id = self.save_report(
            message_id=str(message_id),
            report_date=str(report_date),
            status=status,
            pdf_path=str(pdf_path),
            attachment_name=attachment_name,
            attachment_hash=attachment_hash,
            received_date=str(report.get("received_at", datetime.now().isoformat())),
            processing_date=datetime.now().isoformat(),
            meter_count=meter_count,
            mapped_meter_count=mapped_meter_count,
            missing_meter_count=missing_meter_count,
            total_energy=round(total_energy, 2),
            validation_status=val_status,
            excel_status=exc_status,
            powerbi_status=pbi_status,
            ai_status=ai_stat,
            error_message=err_msg,
        )

        if not report_id:
            rows = self.database.fetch_all(
                "SELECT id FROM reports WHERE message_id = ? AND report_date = ?",
                (str(message_id), str(report_date)),
            )
            if rows:
                report_id = rows[0]["id"]

        if report_id:
            # Clear previous readings if re-recording to maintain idempotency
            self.database.execute("DELETE FROM meter_readings WHERE report_id = ?", (report_id,))
            for r in readings:
                meter_name = r.get("meter_name", "")
                val = r.get("value") if "value" in r else r.get("active_energy")
                unit = r.get("unit", "kWh")
                read_status = r.get("status", "VALID")
                self.save_reading(
                    report_id=report_id,
                    meter_name=meter_name,
                    active_energy=val,
                    unit=unit,
                    status=read_status,
                )

        return report_id

    def get_reports(self, limit: int = 100) -> list[dict]:
        """Fetch processed reports from the database."""
        rows = self.database.fetch_all(
            "SELECT * FROM reports ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]

    def get_recent_history(self, limit: int = 50) -> list[dict]:
        """Alias for recent history."""
        return self.get_reports(limit=limit)

    def get_report_by_date(self, report_date: str) -> dict | None:
        """Fetch report record by date."""
        rows = self.database.fetch_all(
            "SELECT * FROM reports WHERE report_date = ? LIMIT 1",
            (str(report_date),),
        )
        return dict(rows[0]) if rows else None

    def get_readings_for_report(self, report_id: int) -> list[dict]:
        """Fetch all meter readings for a given report ID."""
        rows = self.database.fetch_all(
            "SELECT * FROM meter_readings WHERE report_id = ?",
            (report_id,),
        )
        return [dict(row) for row in rows]

    def get_latest_report(self) -> dict | None:
        """Fetch the most recent processed report."""
        rows = self.database.fetch_all(
            "SELECT * FROM reports ORDER BY id DESC LIMIT 1"
        )
        return dict(rows[0]) if rows else None

    def get_stats(self) -> dict:
        """Calculate high-level summary KPIs."""
        total_rows = self.database.fetch_all("SELECT COUNT(*) as cnt FROM reports")
        success_rows = self.database.fetch_all("SELECT COUNT(*) as cnt FROM reports WHERE status = 'COMPLETED'")
        failed_rows = self.database.fetch_all("SELECT COUNT(*) as cnt FROM reports WHERE status = 'FAILED'")
        energy_rows = self.database.fetch_all("SELECT SUM(total_energy) as total FROM reports WHERE status = 'COMPLETED'")

        total = total_rows[0]["cnt"] if total_rows else 0
        success = success_rows[0]["cnt"] if success_rows else 0
        failed = failed_rows[0]["cnt"] if failed_rows else 0
        energy = energy_rows[0]["total"] if energy_rows and energy_rows[0]["total"] else 0.0

        return {
            "total_reports": total,
            "successful_reports": success,
            "failed_reports": failed,
            "total_energy": round(energy, 2),
        }