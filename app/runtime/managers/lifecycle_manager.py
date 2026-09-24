from app.runtime.models.status import RuntimeStatus


class LifecycleManager:
    def __init__(self) -> None:
        self._status = RuntimeStatus.INITIALIZING

    def get_status(self) -> RuntimeStatus:
        return self._status

    def set_status(self, status: RuntimeStatus) -> None:
        self._status = status