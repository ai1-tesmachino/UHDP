from abc import ABC
from abc import abstractmethod

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)


class BaseDiagnostic(ABC):

    @abstractmethod
    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        pass