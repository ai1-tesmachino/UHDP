from abc import ABC
from abc import abstractmethod

from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)


class ReportRepository(ABC):

    @abstractmethod
    def save(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:
        raise NotImplementedError

    def list_revisions(self, report_name: str) -> list[dict]:
        raise NotImplementedError

    def finalize_revision(
        self,
        report_name: str,
        revision_id: str,
        finalized_by: str | None = None,
    ) -> dict:
        raise NotImplementedError