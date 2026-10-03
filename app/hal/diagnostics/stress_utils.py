from app.hal.diagnostic_request import DiagnosticRequest


def stress_test_duration(request: DiagnosticRequest) -> int:
    raw_duration = request.parameters.get("duration_seconds", 30)
    try:
        duration = int(raw_duration)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "duration_seconds must be an integer between 1 and 30"
        ) from exc
    return min(30, max(1, duration))
