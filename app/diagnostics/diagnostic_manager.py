from app.diagnostics.diagnostic_session import (
    DiagnosticSession,
)


class DiagnosticManager:

    def __init__(
        self,
        registry,
    ) -> None:
        self._registry = registry

    def run(
        self,
        tests: list[str],
    ) -> DiagnosticSession:

        session = DiagnosticSession()

        for test_name in tests:

            if not self._registry.exists(
                test_name,
            ):
                continue

            executor = (
                self._registry.get(
                    test_name,
                )
            )

            result = executor.execute()

            session.result.add_result(
                result,
            )

        return session