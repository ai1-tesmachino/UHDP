class DiagnosticRegistry:

    def __init__(self) -> None:
        self._executors: dict = {}

    def register(
        self,
        name: str,
        executor,
    ) -> None:
        self._executors[name] = executor

    def get(
        self,
        name: str,
    ):
        return self._executors[name]

    def exists(
        self,
        name: str,
    ) -> bool:
        return name in self._executors

    def list(
        self,
    ) -> list[str]:
        return sorted(
            self._executors.keys(),
        )