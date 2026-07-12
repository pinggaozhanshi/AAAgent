"""SQLite connection and schema initialization for AAAgent.

This module deliberately stores only API credential references in SQLite.
Raw API keys belong in Electron safeStorage or another OS credential store.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "aaagent.db"
SCHEMA_PATH = BACKEND_DIR / "schema.sql"


def connect_database(database_path: Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Open a configured SQLite connection for a short repository operation."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database(database_path: Path = DEFAULT_DATABASE_PATH) -> None:
    """Create all v0.1.3 tables if they do not already exist."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect_database(database_path) as connection:
        connection.executescript(schema)


if __name__ == "__main__":
    initialize_database()
    print(f"AAAgent SQLite database initialized at: {DEFAULT_DATABASE_PATH}")