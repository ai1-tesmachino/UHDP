from app.hal.diagnostic_registry import (
    DiagnosticRegistry,
)


def test_register_and_get():
    registry = DiagnosticRegistry()

    diagnostic = object()

    registry.register(
        "cpu",
        diagnostic,
    )

    assert registry.exists(
        "cpu",
    )

    assert (
        registry.get("cpu")
        is diagnostic
    )


def test_list_diagnostics():
    registry = DiagnosticRegistry()

    registry.register(
        "cpu",
        object(),
    )

    registry.register(
        "memory",
        object(),
    )

    diagnostics = (
        registry.list_diagnostics()
    )

    assert diagnostics == [
        "cpu",
        "memory",
    ]