import json
from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from app.core.config import get_settings
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.report_repository import (
    ReportRepository,
)


class FileReportRepository(
    ReportRepository,
):

    def __init__(
        self,
        directory: str | Path | None = None,
    ) -> None:

        settings = get_settings()

        self._directory = Path(
            directory
            or settings.REPORTS_DIRECTORY
        )

        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:
        payload = self._create_report_payload(report)
        html = self._build_html(report)
        revisions = self.list_revisions(report_name)
        if any(
            revision.get("revision_id") == report.revision_id
            for revision in revisions
        ):
            self._save_revision(report_name, report, payload, html)
            return
        latest = revisions[-1] if revisions else None
        if latest is not None and latest.get("finalized_at") is not None:
            if (
                report.supersedes_revision_id != latest.get("revision_id")
                or not report.supersession_reason
                or not report.superseded_by
            ):
                raise ValueError(
                    "A finalized report requires an explicit, attributed superseding revision."
                )
        elif any(
            value is not None
            for value in (
                report.supersedes_revision_id,
                report.supersession_reason,
                report.superseded_by,
            )
        ):
            raise ValueError("A report can supersede only a finalized revision.")
        self._save_revision(report_name, report, payload, html)

    def save_json(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:
        self.save(report_name, report)

    def save_html(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:
        self.save(report_name, report)

    def list_revisions(self, report_name: str) -> list[dict]:
        revision_dir = self._revision_directory(report_name)
        revisions = []
        if not revision_dir.exists():
            return revisions
        for path in sorted(
            revision_dir.glob("*.json"),
            key=lambda item: int(item.stem),
        ):
            with open(path, "r", encoding="utf-8") as file:
                revisions.append(json.load(file))
        return revisions

    def finalize_revision(
        self,
        report_name: str,
        revision_id: str,
        finalized_by: str | None = None,
    ) -> dict:
        revisions = self.list_revisions(report_name)
        if not revisions or revisions[-1].get("revision_id") != revision_id:
            raise ValueError("Only the latest report revision can be finalized.")
        latest = revisions[-1]
        if latest.get("finalized_at") is None:
            latest["finalized_at"] = datetime.now(UTC).isoformat()
            latest["finalized_by"] = finalized_by
            revision_path = self._revision_directory(report_name) / (
                f"{latest['revision']}.json"
            )
            with open(revision_path, "w", encoding="utf-8") as file:
                json.dump(latest, file, indent=4, default=str)
            current_path = self._directory / f"{report_name}.json"
            if current_path.exists():
                with open(current_path, "r", encoding="utf-8") as file:
                    current = json.load(file)
                if current.get("revision_id") == revision_id:
                    current.update(
                        finalized_at=latest["finalized_at"],
                        finalized_by=finalized_by,
                    )
                    with open(current_path, "w", encoding="utf-8") as file:
                        json.dump(current, file, indent=4, default=str)
        return {
            "finalized_at": latest.get("finalized_at"),
            "finalized_by": latest.get("finalized_by"),
        }

    def _revision_directory(self, report_name: str) -> Path:
        return self._directory / f"{report_name}.revisions"

    def _write_json(self, path: Path, payload: dict) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, default=str)

    def _write_html(self, path: Path, contents: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(contents)

    def _save_revision(
        self,
        report_name: str,
        report: DiagnosticReport,
        payload: dict,
        html: str,
    ) -> None:
        revisions = self.list_revisions(report_name)
        existing_revision = next(
            (
                revision
                for revision in revisions
                if revision.get("revision_id") == report.revision_id
            ),
            None,
        )
        if existing_revision is not None:
            if (
                {
                    key: value
                    for key, value in existing_revision.items()
                    if key not in {
                        "revision",
                        "finalized_at",
                        "finalized_by",
                        "html",
                    }
                }
                == payload
                and existing_revision.get("html") == html
            ):
                return
            raise ValueError(
                f"Report revision_id already exists: {report.revision_id}"
            )
        revision_number = (
            int(revisions[-1]["revision"]) + 1 if revisions else 1
        )
        revision_payload = {
            **payload,
            "revision": revision_number,
            "finalized_at": None,
            "finalized_by": None,
            "html": html,
        }
        revision_dir = self._revision_directory(report_name)
        revision_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            revision_dir / f"{revision_number}.json",
            revision_payload,
        )
        self._write_html(revision_dir / f"{revision_number}.html", html)
        self._write_json(self._directory / f"{report_name}.json", payload)
        self._write_html(self._directory / f"{report_name}.html", html)

    def _build_html(
        self,
        report: DiagnosticReport,
    ) -> str:

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>UHDP Diagnostic Report</title>
</head>
<body>

<h1>UHDP Diagnostic Report</h1>

<p><strong>Report ID:</strong> {report.report_id}</p>
<p><strong>Device ID:</strong> {report.device_id}</p>
<p><strong>Status:</strong> {report.status}</p>
<p><strong>Created:</strong> {report.created_at}</p>

<pre>{json.dumps(
    self._serialize(report.data),
    indent=4,
    default=str,
)}</pre>

</body>
</html>
"""

    def get_json(
        self,
        report_name: str,
    ) -> dict | None:

        file_path = (
            self._directory
            / f"{report_name}.json"
        )

        if not file_path.exists():
            return None

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def get_html(
        self,
        report_name: str,
    ) -> str | None:
        file_path = self._directory / f"{report_name}.html"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def list_reports(
        self,
    ) -> list[str]:

        reports = []

        for file in self._directory.glob(
            "*.json"
        ):
            reports.append(
                file.stem
            )

        reports.sort()

        return reports

    def _create_report_payload(
        self,
        report: DiagnosticReport,
    ) -> dict:

        return {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "supersedes_revision_id": report.supersedes_revision_id,
            "supersession_reason": report.supersession_reason,
            "superseded_by": report.superseded_by,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": (
                report.created_at.isoformat()
            ),
            "data": self._serialize(
                report.data
            ),
        }

    def _serialize(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            Enum,
        ):
            return value.value

        if is_dataclass(
            value
        ):
            return self._serialize(
                asdict(value)
            )

        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._serialize(item)
                for key, item in value.items()
            }

        if isinstance(
            value,
            list,
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        return value