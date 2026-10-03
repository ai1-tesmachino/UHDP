from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)


class ManualTestRegistry:

    def __init__(self) -> None:
        self._results: dict[
            str,
            ManualTestResult,
        ] = {}

    def record(
        self,
        result: ManualTestResult,
    ) -> None:
        self._results[
            result.test_name
        ] = result

    def get(
        self,
        test_name: str,
    ) -> ManualTestResult | None:
        return self._results.get(
            test_name,
        )

    def all(self) -> list[
        ManualTestResult
    ]:
        return list(
            self._results.values()
        )