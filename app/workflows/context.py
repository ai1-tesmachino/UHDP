class WorkflowContext:

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def set(
        self,
        key: str,
        value: object,
    ) -> None:
        self._data[key] = value

    def get(
        self,
        key: str,
        default: object | None = None,
    ) -> object | None:
        return self._data.get(
            key,
            default,
        )

    def has(
        self,
        key: str,
    ) -> bool:
        return key in self._data

    def remove(
        self,
        key: str,
    ) -> None:
        self._data.pop(
            key,
            None,
        )

    def clear(
        self,
    ) -> None:
        self._data.clear()

    def to_dict(
        self,
    ) -> dict[str, object]:
        return dict(
            self._data,
        )