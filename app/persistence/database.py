from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class Database:

    def __init__(
        self,
        path: str,
    ):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def connect(self):
        connection = sqlite3.connect(
            str(self.path)
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def initialize(self):

        with self.connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT,
                    report_date TEXT,
                    status TEXT,
                    pdf_path TEXT,
                    attachment_name TEXT,
                    attachment_hash TEXT,
                    received_date TEXT,
                    processing_date TEXT,
                    meter_count INTEGER DEFAULT 0,
                    mapped_meter_count INTEGER DEFAULT 0,
                    missing_meter_count INTEGER DEFAULT 0,
                    total_energy REAL DEFAULT 0.0,
                    validation_status TEXT,
                    excel_status TEXT,
                    powerbi_status TEXT,
                    ai_status TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id, report_date)
                )
                """
            )

            # Auto-migrate existing databases that may lack new audit columns
            existing_cols = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(reports)").fetchall()
            }
            new_cols = {
                "attachment_name": "TEXT",
                "attachment_hash": "TEXT",
                "received_date": "TEXT",
                "processing_date": "TEXT",
                "meter_count": "INTEGER DEFAULT 0",
                "mapped_meter_count": "INTEGER DEFAULT 0",
                "missing_meter_count": "INTEGER DEFAULT 0",
                "total_energy": "REAL DEFAULT 0.0",
                "validation_status": "TEXT",
                "excel_status": "TEXT",
                "powerbi_status": "TEXT",
                "ai_status": "TEXT",
                "retry_count": "INTEGER DEFAULT 0",
                "error_message": "TEXT",
            }
            for col_name, col_def in new_cols.items():
                if col_name not in existing_cols:
                    try:
                        connection.execute(
                            f"ALTER TABLE reports ADD COLUMN {col_name} {col_def}"
                        )
                    except Exception:
                        pass

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS meter_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    meter_name TEXT,
                    active_energy REAL,
                    unit TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.commit()

    def execute(
        self,
        query: str,
        parameters: Iterable = (),
    ):

        with self.connect() as connection:

            cursor = connection.execute(
                query,
                tuple(parameters),
            )

            connection.commit()

            return cursor

    def fetch_all(
        self,
        query: str,
        parameters: Iterable = (),
    ):

        with self.connect() as connection:

            cursor = connection.execute(
                query,
                tuple(parameters),
            )

            return cursor.fetchall()