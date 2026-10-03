from app.diagnostics.diagnostic_manager import (
    DiagnosticManager,
)
from app.diagnostics.diagnostic_registry import (
    DiagnosticRegistry,
)

from app.diagnostics.executors.cpu_executor import (
    CpuExecutor,
)
from app.diagnostics.executors.memory_executor import (
    MemoryExecutor,
)
from app.diagnostics.executors.storage_executor import (
    StorageExecutor,
)


def create_registry() -> DiagnosticRegistry:

    registry = DiagnosticRegistry()

    registry.register(
        "cpu",
        CpuExecutor(),
    )

    registry.register(
        "memory",
        MemoryExecutor(),
    )

    registry.register(
        "storage",
        StorageExecutor(),
    )

    return registry