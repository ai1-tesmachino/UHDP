from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.models.diagnostic_result_collection import (
    DiagnosticResultCollection,
)


def make_result(
    diagnostic_id: str,
    diagnostic_type: str,
    status: DiagnosticStatus,
) -> DiagnosticResult:
    return DiagnosticResult(
        diagnostic_id=diagnostic_id,
        diagnostic_type=diagnostic_type,
        device_id="test-device",
        status=status,
        message="test",
    )


def test_add_and_summary():
    collection = DiagnosticResultCollection()

    collection.add(
        make_result(
            "cpu-1",
            "cpu",
            DiagnosticStatus.PASSED,
        )
    )

    collection.add(
        make_result(
            "memory-1",
            "memory",
            DiagnosticStatus.FAILED,
        )
    )

    collection.add(
        make_result(
            "storage-1",
            "storage",
            DiagnosticStatus.ERROR,
        )
    )

    summary = collection.summary()

    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.errors == 1


def test_extend():
    collection = DiagnosticResultCollection()

    results = [
        make_result(
            "cpu-1",
            "cpu",
            DiagnosticStatus.PASSED,
        ),
        make_result(
            "memory-1",
            "memory",
            DiagnosticStatus.PASSED,
        ),
    ]

    collection.extend(results)

    assert len(collection) == 2


def test_get_by_diagnostic_id():
    collection = DiagnosticResultCollection()

    result = make_result(
        "cpu-1",
        "cpu",
        DiagnosticStatus.PASSED,
    )

    collection.add(result)

    assert collection.get("cpu-1") is result
    assert collection.get("missing") is None


def test_by_type():
    collection = DiagnosticResultCollection()

    collection.extend(
        [
            make_result(
                "cpu-1",
                "cpu",
                DiagnosticStatus.PASSED,
            ),
            make_result(
                "cpu-2",
                "cpu",
                DiagnosticStatus.FAILED,
            ),
            make_result(
                "memory-1",
                "memory",
                DiagnosticStatus.PASSED,
            ),
        ]
    )

    cpu_results = collection.by_type("cpu")

    assert len(cpu_results) == 2
    assert all(
        result.diagnostic_type == "cpu"
        for result in cpu_results
    )


def test_clear():
    collection = DiagnosticResultCollection()

    collection.add(
        make_result(
            "cpu-1",
            "cpu",
            DiagnosticStatus.PASSED,
        )
    )

    collection.clear()

    assert len(collection) == 0