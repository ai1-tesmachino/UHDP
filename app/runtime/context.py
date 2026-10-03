from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings

from app.plugins.loader import PluginLoader
from app.plugins.manager import PluginManager
from app.plugins.registry import PluginRegistry

from app.runtime.background.task_manager import TaskManager
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.managers.lifecycle_manager import LifecycleManager
from app.runtime.managers.state_manager import StateManager
from app.runtime.registry import RuntimeRegistry

from app.runtime.workflow.service_container import ServiceContainer

from app.workflows.execution.audit_trail import AuditTrail
from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)
from app.workflows.persistence.file_repository import (
    FileWorkflowRepository,
)
from app.workflows.templates.file_template_repository import (
    FileTemplateRepository,
)
from app.workflows.validation.validator import (
    create_default_validator,
)


class RuntimeContext:
    def __init__(
        self,
        data_dir: str | Path | None = None,
    ) -> None:
        self.registry = RuntimeRegistry()

        self.state_manager = StateManager()
        self.event_bus = EventBus()
        self.task_manager = TaskManager()
        self.job_manager = JobManager()
        self.lifecycle_manager = LifecycleManager()

        settings = get_settings()

        self.data_dir = Path(
            data_dir or settings.DATA_DIR
        )

        self.workflow_repository = FileWorkflowRepository(
            self.data_dir / "workflows"
        )

        self.execution_repository = FileExecutionRepository(
            self.data_dir / "executions"
        )

        self.template_repository = FileTemplateRepository(
            self.data_dir / "templates"
        )

        self.workflow_validator = create_default_validator()
        self.audit_trail = AuditTrail()

        self.services = ServiceContainer(
            workflow_repository=self.workflow_repository,
            execution_repository=self.execution_repository,
            template_repository=self.template_repository,
            validator=self.workflow_validator,
            audit_trail=self.audit_trail,
        )

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

        self.registry.register(
            "workflow_repository",
            self.workflow_repository,
        )

        self.registry.register(
            "execution_repository",
            self.execution_repository,
        )

        self.registry.register(
            "template_repository",
            self.template_repository,
        )

        self.registry.register(
            "workflow_validator",
            self.workflow_validator,
        )

        self.registry.register(
            "audit_trail",
            self.audit_trail,
        )

        self.registry.register(
            "workflow_service",
            self.services.workflow_service,
        )

        self.registry.register(
            "workflow_runner",
            self.services.workflow_runner,
        )

        self.registry.register(
            "execution_service",
            self.services.execution_service,
        )

        self.registry.register(
            "template_service",
            self.services.template_service,
        )

        await self.plugin_manager.load(
            "app.plugins.system.diagnostics.plugin"
        )

        await self.job_manager.start()

    async def stop(self) -> None:
        print("CONTEXT STOP: before", self.job_manager.scheduler.running)

        await self.job_manager.stop()

        print("CONTEXT STOP: after", self.job_manager.scheduler.running)
