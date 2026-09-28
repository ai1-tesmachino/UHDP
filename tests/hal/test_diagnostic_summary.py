from app.hal.models.diagnostic_summary import (
    DiagnosticSummary,
)


def test_summary_defaults():
    summary = DiagnosticSummary()

    assert summary.total == 0
    assert summary.passed == 0
    assert summary.failed == 0
    assert summary.errors == 0