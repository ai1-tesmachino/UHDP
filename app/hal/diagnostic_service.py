from app.hal.default_diagnostics import (
    create_default_registry,
)
from app.hal.device_manager import (
    DeviceManager,
)
from app.hal.diagnostic_executor import (
    DiagnosticExecutor,
)
from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.adapters.local_adapter import (
    LocalAdapter,
)


class DiagnosticService:

    def __init__(self) -> None:
        self._device_manager = DeviceManager(
            LocalAdapter(),
        )

        self._registry = (
            create_default_registry()
        )

        self._executor = (
            DiagnosticExecutor(
                self._registry,
            )
        )

    @property
    def registry(self):
        return self._registry

    def get_device(self):
        return self._device_manager.get_device()

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        return self._executor.execute(
            request,
        )