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