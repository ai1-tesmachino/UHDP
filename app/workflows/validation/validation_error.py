from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ValidationError:
    code: str
    message: str
    path: str = ""