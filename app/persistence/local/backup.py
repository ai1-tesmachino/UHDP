from __future__ import annotations

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase


def backup_database(
    database: SQLiteDatabase,
    destination_directory: str | Path | None = None,
) -> Path:
    settings = get_settings()
    directory = Path(
        destination_directory or Path(settings.DATA_DIR) / "Backups"
    )
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = directory / f"uhdp-{timestamp}-{uuid.uuid4()}.sqlite3"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".uhdp-backup-",
        suffix=".tmp",
        dir=directory,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        source_connection = sqlite3.connect(database.path, timeout=30)
        destination_connection = sqlite3.connect(temporary, timeout=30)
        try:
            source_connection.backup(destination_connection)
            check = destination_connection.execute("PRAGMA integrity_check").fetchone()
            if check is None or check[0] != "ok":
                raise RuntimeError("SQLite backup integrity check failed.")
        finally:
            destination_connection.close()
            source_connection.close()
        os.chmod(temporary, 0o600)
        with temporary.open("rb+") as backup_file:
            os.fsync(backup_file.fileno())
        os.link(temporary, destination)
        temporary.unlink()
        _fsync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an atomic UHDP SQLite backup.")
    parser.add_argument("--destination", help="Backup directory (default: DATA_DIR/Backups).")
    args = parser.parse_args()
    result = backup_database(SQLiteDatabase(), args.destination)
    print(result)


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


if __name__ == "__main__":
    main()
