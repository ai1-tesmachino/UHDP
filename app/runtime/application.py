
from __future__ import annotations

from app.runtime.context import RuntimeContext
from app.runtime.models.status import RuntimeStatus


class Application:
    def __init__(
        self,
        runtime: RuntimeContext | None = None,
    ) -> None:
        self.runtime = runtime or RuntimeContext()

    @property
    def status(self) -> RuntimeStatus:
        return self.runtime.lifecycle_manager.get_status()

    async def start(self) -> None:
        if self.status is RuntimeStatus.RUNNING:
            return

        if self.status is RuntimeStatus.STOPPING:
            raise RuntimeError(
                "Application is stopping"
            )

        if self.status is RuntimeStatus.STOPPED:
            raise RuntimeError(
                "Application cannot be restarted"
            )

        await self.runtime.start()

        self.runtime.lifecycle_manager.set_status(
            RuntimeStatus.RUNNING
        )

    async def stop(self) -> None:
        if self.status is RuntimeStatus.STOPPED:
            return

        self.runtime.lifecycle_manager.set_status(
            RuntimeStatus.STOPPING
        )

        try:
            await self.runtime.stop()
        finally:
            self.runtime.lifecycle_manager.set_status(
                RuntimeStatus.STOPPED
            )
