from app.workflows.action import Action
from app.workflows.workflow_context import WorkflowContext
from app.workflows.manual.manual_test_manager import (
    ManualTestManager,
)
from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)


class RunManualTestAction(Action):

    def __init__(
        self,
        manager: ManualTestManager,
        test_name: str,
        passed: bool,
        notes: str = "",
    ) -> None:
        self._manager = manager
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

        self._manager.record(
            result,
        )

        context.set(
            f"manual.{self._test_name}",
            result,
        )