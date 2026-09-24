from __future__ import annotations

from app.plugins.loader import PluginLoader
from app.plugins.manager import PluginManager
from app.plugins.registry import PluginRegistry

from app.runtime.background.task_manager import TaskManager
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.managers.lifecycle_manager import LifecycleManager
from app.runtime.managers.state_manager import StateManager
from app.runtime.registry import RuntimeRegistry


class RuntimeContext:
    def __init__(self) -> None:
        self.registry = RuntimeRegistry()

        self.state_manager = StateManager()
        self.event_bus = EventBus()
        self.task_manager = TaskManager()
        self.job_manager = JobManager()
        self.lifecycle_manager = LifecycleManager()

        self.plugin_registry: PluginRegistry | None = None
        self.plugin_loader: PluginLoader | None = None
        self.plugin_manager: PluginManager | None = None

    async def start(self) -> None:
        self.plugin_registry = PluginRegistry()

        self.plugin_loader = PluginLoader()

        self.plugin_manager = PluginManager(
            registry=self.plugin_registry,
            loader=self.plugin_loader,
            runtime=self,
        )

        self.registry.register(
            "state_manager",
            self.state_manager,
        )

        self.registry.register(
            "event_bus",
            self.event_bus,
        )

        self.registry.register(
            "task_manager",
            self.task_manager,
        )

        self.registry.register(
            "job_manager",
            self.job_manager,
        )

        self.registry.register(
            "plugin_registry",
            self.plugin_registry,
        )

        self.registry.register(
            "plugin_loader",
            self.plugin_loader,
        )

        self.registry.register(
            "plugin_manager",
            self.plugin_manager,
        )

        await self.plugin_manager.load(
            "app.plugins.system.diagnostics.plugin"
        )

        print(
            [
                p.metadata.name
                for p in self.plugin_manager.list()
            ]
        )

        await self.job_manager.start()

    async def stop(self) -> None:
        await self.job_manager.stop()