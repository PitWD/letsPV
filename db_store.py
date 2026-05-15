from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union


ScalarValue = Union[str, int, float]


def _connect_rw(db_path: Union[str, Path]) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), timeout=5)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con


def init_db(db_path: Union[str, Path]) -> None:
    with _connect_rw(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                name TEXT NOT NULL,
                num_value REAL,
                text_value TEXT,
                UNIQUE(ts, name)
            );

            CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_measurements_name_ts ON measurements(name, ts DESC);
            """
        )


def write_measurement(
    db_path: Union[str, Path],
    measured_at: datetime,
    values: Mapping[str, ScalarValue],
) -> None:
    if not values:
        return

    ts = measured_at.isoformat(timespec="seconds")
    rows = []
    for name, value in values.items():
        if isinstance(value, (int, float)):
            rows.append((ts, name, float(value), None))
        else:
            rows.append((ts, name, None, str(value)))

    with _connect_rw(db_path) as con:
        con.executemany(
            """
            INSERT INTO measurements (ts, name, num_value, text_value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ts, name) DO UPDATE SET
                num_value = excluded.num_value,
                text_value = excluded.text_value
            """,
            rows,
        )


def read_latest(
    db_path: Union[str, Path],
    limit: int = 20,
    name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []

    query = (
        "SELECT ts, name, num_value, text_value "
        "FROM measurements "
        + ("WHERE name = ? " if name else "")
        + "ORDER BY ts DESC, name ASC LIMIT ?"
    )

    uri = f"file:{Path(db_path)}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as con:
        con.execute("PRAGMA busy_timeout=5000;")
        if name:
            cur = con.execute(query, (name, limit))
        else:
            cur = con.execute(query, (limit,))
        rows = cur.fetchall()

    return [
        {
            "ts": row[0],
            "name": row[1],
            "num_value": row[2],
            "text_value": row[3],
        }
        for row in rows
    ]