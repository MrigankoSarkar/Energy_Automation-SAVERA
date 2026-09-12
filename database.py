from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class AppDatabase:

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self):
        return sqlite3.connect(
            self.db_path,
            timeout=30,
        )

    def _initialize(self):
        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    report_date TEXT,
                    subject TEXT,
                    processed_at TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    level TEXT,
                    stage TEXT,
                    message TEXT
                )
                """
            )

    def is_processed(self, message_id: str) -> bool:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT 1
                FROM processed_messages
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()

        return row is not None

    def mark_processed(
        self,
        message_id: str,
        report_date: str,
        subject: str,
    ):

        with self._connect() as connection:

            connection.execute(
                """
                INSERT OR REPLACE INTO processed_messages
                (
                    message_id,
                    report_date,
                    subject,
                    processed_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    message_id,
                    report_date,
                    subject,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

    def log(
        self,
        level: str,
        stage: str,
        message: str,
    ):

        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO activity
                (
                    timestamp,
                    level,
                    stage,
                    message
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    level,
                    stage,
                    message,
                ),
            )

    def recent_activity(
        self,
        limit: int = 50,
    ):

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    timestamp,
                    level,
                    stage,
                    message
                FROM activity
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "timestamp": row[0],
                "level": row[1],
                "stage": row[2],
                "message": row[3],
            }
            for row in rows
        ]