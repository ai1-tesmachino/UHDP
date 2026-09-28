import pytest

from app.runtime.application import Application
from app.runtime.models.status import RuntimeStatus


class FailingRuntime:
    def __init__(self) -> None:
        from app.runtime.managers.lifecycle_manager import (
            LifecycleManager,
        )

        self.lifecycle_manager = LifecycleManager()

    async def start(self) -> None:
        raise RuntimeError("startup failed")

    async def stop(self) -> None:
        pass


@pytest.mark.asyncio
async def test_application_start_failure_does_not_enter_running_state():
    runtime = FailingRuntime()
    application = Application(runtime=runtime)

    with pytest.raises(
        RuntimeError,
        match="startup failed",
    ):
        await application.start()

    assert application.status is RuntimeStatus.INITIALIZING
