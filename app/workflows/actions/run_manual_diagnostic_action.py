from app.workflows.action import Action
from app.workflows.context import WorkflowContext
from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)
from app.workflows.manual.manual_test_registry import (
    ManualTestRegistry,
)


class RunManualDiagnosticAction(
    Action,
):

    def __init__(
        self,
        registry: ManualTestRegistry,
        test_name: str,
        passed: bool,
        notes: str = "",
    ) -> None:
        self._registry = registry
        self._test_name = test_name
        self._passed = passed
        self._notes = notes

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        result = ManualTestResult(
            test_name=self._test_name,
            passed=self._passed,
            notes=self._notes,
        )

        self._registry.record(
            result,
        )

        context.set(
            f"manual.{self._test_name}",
            result,
        )