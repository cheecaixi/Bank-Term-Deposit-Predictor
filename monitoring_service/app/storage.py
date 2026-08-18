import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import LOG_RETENTION_LIMIT, MONITORING_DATABASE_PATH
from app.schemas import LogCreate


def _connect() -> sqlite3.Connection:
    database_path = Path(MONITORING_DATABASE_PATH)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                level TEXT NOT NULL,
                event TEXT NOT NULL,
                method TEXT,
                endpoint TEXT,
                status_code INTEGER,
                response_time_ms REAL,
                message TEXT NOT NULL,
                metadata TEXT
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_system_logs_timestamp "
            "ON system_logs (timestamp DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_system_logs_service_level "
            "ON system_logs (service, level)"
        )


def add_log(log: LogCreate) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO system_logs (
                timestamp, service, level, event, method, endpoint,
                status_code, response_time_ms, message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                log.service,
                log.level,
                log.event,
                log.method,
                log.endpoint,
                log.status_code,
                log.response_time_ms,
                log.message,
                json.dumps(log.metadata) if log.metadata is not None else None,
            ),
        )
        connection.execute(
            """
            DELETE FROM system_logs
            WHERE log_id NOT IN (
                SELECT log_id FROM system_logs
                ORDER BY log_id DESC LIMIT ?
            )
            """,
            (LOG_RETENTION_LIMIT,),
        )
        log_id = cursor.lastrowid

    return get_log(log_id)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["metadata"] = (
        json.loads(result["metadata"])
        if result["metadata"] is not None
        else None
    )
    return result


def get_log(log_id: int) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM system_logs WHERE log_id = ?",
            (log_id,),
        ).fetchone()
    return _row_to_dict(row)


def get_logs(
    limit: int,
    service: Optional[str] = None,
    level: Optional[str] = None,
) -> list[dict[str, Any]]:
    conditions = []
    parameters: list[Any] = []
    if service:
        conditions.append("service = ?")
        parameters.append(service)
    if level:
        conditions.append("level = ?")
        parameters.append(level)

    where_clause = (
        " WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )
    parameters.append(limit)

    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM system_logs"
            + where_clause
            + " ORDER BY log_id DESC LIMIT ?",
            parameters,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_metrics() -> dict[str, Any]:
    with _connect() as connection:
        totals = connection.execute(
            """
            SELECT
                COUNT(*) AS total_logs,
                SUM(CASE WHEN level IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END)
                    AS total_errors,
                SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END)
                    AS total_warnings,
                AVG(response_time_ms) AS average_response_time_ms,
                MAX(response_time_ms) AS maximum_response_time_ms
            FROM system_logs
            """
        ).fetchone()
        by_service = connection.execute(
            """
            SELECT service, COUNT(*) AS total_logs,
                SUM(CASE WHEN level IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END)
                    AS errors,
                AVG(response_time_ms) AS average_response_time_ms
            FROM system_logs
            GROUP BY service
            ORDER BY service
            """
        ).fetchall()

    return {
        **dict(totals),
        "by_service": [dict(row) for row in by_service],
    }
