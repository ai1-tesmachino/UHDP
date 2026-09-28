class ActionRegistry:

    def __init__(self) -> None:
        self._actions: dict[str, type] = {}

    def register(
        self,
        name: str,
        action_type: type,
    ) -> None:
        self._actions[name] = action_type

    def get(
        self,
        name: str,
    ) -> type:
        return self._actions[name]

    def exists(
        self,
        name: str,
    ) -> bool:
        return name in self._actions

    def all(self) -> dict[str, type]:
        return dict(self._actions)