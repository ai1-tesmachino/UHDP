from dataclasses import dataclass


@dataclass(slots=True)
class ManualTestResult:
    test_name: str
    passed: bool
    notes: str = ""