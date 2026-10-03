from app.diagnostics import (
    create_registry,
)
from app.diagnostics.diagnostic_manager import (
    DiagnosticManager,
)


def test_run_cpu_memory_storage():

    registry = create_registry()

    manager = DiagnosticManager(
        registry,
    )

    session = manager.run(
        [
            "cpu",
            "memory",
            "storage",
        ]
    )

    assert len(
        session.result.results
    ) == 3