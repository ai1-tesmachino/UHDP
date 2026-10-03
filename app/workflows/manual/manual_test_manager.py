from app.workflows.manual.manual_test_definition import (
    ManualTestDefinition,
)
from app.workflows.manual.manual_test_registry import (
    ManualTestRegistry,
)
from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)


class ManualTestManager:

    def __init__(
        self,
        registry: ManualTestRegistry | None = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else ManualTestRegistry()
        )

        self._definitions: dict[
            str,
            ManualTestDefinition,
        ] = {}

    def register(
        self,
        definition: ManualTestDefinition,
    ) -> None:
        self._definitions[
            definition.test_name
        ] = definition

    def get(
        self,
        test_name: str,
    ) -> ManualTestDefinition | None:
        return self._definitions.get(
            test_name,
        )

    def all(
        self,
    ) -> list[ManualTestDefinition]:
        return list(
            self._definitions.values()
        )

    def record(
        self,
        result: ManualTestResult,
    ) -> None:
        self.registry.record(
            result,
        )

    def result(
        self,
        test_name: str,
    ) -> ManualTestResult | None:
        return self.registry.get(
            test_name,
        )

    def results(
        self,
    ) -> list[ManualTestResult]:
        return self.registry.all()