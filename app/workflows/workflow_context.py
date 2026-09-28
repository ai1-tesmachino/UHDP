# app/workflows/workflow_context.py

class WorkflowContext:

    def __init__(self) -> None:
        self._variables: dict[str, object] = {}

    def set(
        self,
        key: str,
        value: object,
    ) -> None:
        self._variables[key] = value

    def get(
        self,
        key: str,
        default: object = None,
    ) -> object:
        return self._variables.get(key, default)

    def exists(
        self,
        key: str,
    ) -> bool:
        return key in self._variables