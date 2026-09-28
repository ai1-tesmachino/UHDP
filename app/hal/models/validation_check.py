from dataclasses import dataclass


@dataclass(slots=True)
class ValidationCheck:
    name: str
    passed: bool
    message: str