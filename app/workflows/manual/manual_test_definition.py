from dataclasses import dataclass


@dataclass(slots=True)
class ManualTestDefinition:
    test_name: str
    description: str = ""
    required: bool = True