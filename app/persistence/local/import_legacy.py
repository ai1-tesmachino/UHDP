from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase


def import_legacy_files(
    database: SQLiteDatabase,
    sessions_directory: str | Path,
    report_directories: list[str | Path],
) -> dict[str, int]:
    """Import JSON records once without creating cloud-sync outbox events."""
    imported = {"sessions": 0, "reports": 0, "skipped": 0}

    sessions_path = Path(sessions_directory)
    if sessions_path.exists():
        for path in sorted(sessions_path.glob("*.json")):
            payload = _read_object(path)
            session_id = payload.get("session_id")
            if not isinstance(session_id, str) or not session_id:
                raise ValueError(f"{path} does not contain a valid session_id.")
            if database.save_session(
                session_id,
                payload,
                enqueue_sync=False,
                only_if_missing=True,
            ):
                imported["sessions"] += 1
            else:
                imported["skipped"] += 1

    seen_directories: set[Path] = set()
    for raw_directory in report_directories:
        directory = Path(raw_directory)
        try:
            normalized_directory = directory.resolve()
        except OSError:
            normalized_directory = directory.absolute()
        if normalized_directory in seen_directories:
            continue
        seen_directories.add(normalized_directory)
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            payload = _read_object(path)
            report_id = path.stem
            html_path = path.with_suffix(".html")
            html_content = (
                html_path.read_text(encoding="utf-8")
                if html_path.is_file()
                else None
            )
            if database.save_report(
                report_id,
                payload,
                html_content,
                enqueue_sync=False,
                only_if_missing=True,
            ):
                imported["reports"] += 1
            else:
                imported["skipped"] += 1
    return imported


def _read_object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Import existing UHDP JSON sessions and reports into local SQLite."
    )
    parser.add_argument(
        "--sessions",
        default=settings.SESSIONS_DIRECTORY,
        help="Legacy session JSON directory.",
    )
    parser.add_argument(
        "--reports",
        action="append",
        dest="report_directories",
        help="Legacy report JSON directory; repeat for each directory.",
    )
    args = parser.parse_args()

    report_directories = args.report_directories or [
        settings.REPORTS_DIRECTORY,
        "reports",
    ]
    summary = import_legacy_files(
        SQLiteDatabase(),
        args.sessions,
        report_directories,
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
