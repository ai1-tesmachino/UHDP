from dataclasses import dataclass


@dataclass(slots=True)
class TestCase:
    name: str
    executor: str
    enabled: bool = True