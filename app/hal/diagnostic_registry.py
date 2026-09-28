class DiagnosticRegistry:

    def __init__(self) -> None:
        self._diagnostics: dict[str, object] = {}

    def register(
        self,
        diagnostic_type: str,
        diagnostic: object,
    ) -> None:
        self._diagnostics[
            diagnostic_type
        ] = diagnostic

    def get(
        self,
        diagnostic_type: str,
    ) -> object:
        return self._diagnostics[
            diagnostic_type
        ]

    def exists(
        self,
        diagnostic_type: str,
    ) -> bool:
        return (
            diagnostic_type
            in self._diagnostics
        )

    def list_diagnostics(
        self,
    ) -> list[str]:
        return sorted(
            self._diagnostics.keys()
        )