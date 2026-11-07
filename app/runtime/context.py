from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from pathlib import Path

from app.core.config import get_settings
from app.plugins.loader import PluginLoader
from app.plugins.manager import PluginManager
from app.plugins.registry import PluginRegistry
from app.runtime.background.task_manager import TaskManager
from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.managers.lifecycle_manager import LifecycleManager
from app.runtime.managers.state_manager import StateManager
from app.runtime.models.status import RuntimeStatus
from app.runtime.models.runtime import RuntimeHealth
from app.runtime.registry import RuntimeRegistry
from app.runtime.scheduler.async_scheduler import RuntimeScheduler
from app.runtime.workflow.service_container import ServiceContainer
from app.websocket.bridge import EventBridge
from app.websocket.manager import WebSocketManager
from app.workflows.execution.audit_trail import AuditTrail
from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)
from app.workflows.persistence.file_repository import FileWorkflowRepository
from app.workflows.templates.file_template_repository import FileTemplateRepository
from app.workflows.validation.validator import create_default_validator

logger = logging.getLogger(__name__)


class RuntimeContext:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.registry = RuntimeRegistry()
        self.state_manager = StateManager()
        self.event_bus = EventBus()
        self.task_manager = TaskManager()
        self.scheduler = RuntimeScheduler(self.event_bus)
        self.job_manager = JobManager(
            self.event_bus,
            scheduler=self.scheduler.scheduler,
        )
        self.lifecycle_manager = LifecycleManager()
        self.websocket_manager = WebSocketManager()
        self.event_bridge = EventBridge(self.event_bus, self.websocket_manager)

        settings = get_settings()
        self.data_dir = Path(data_dir or settings.DATA_DIR)
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
        self._started_at: datetime | None = None
        self._last_health_check = datetime.now(UTC)
        self._start_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._start_lock:
            status = self.lifecycle_manager.get_status()
            if status is RuntimeStatus.RUNNING:
                return
            if status in (RuntimeStatus.STOPPING, RuntimeStatus.STOPPED):
                raise RuntimeError(f"Runtime cannot start from {status.value}")

            try:
                await self._register_components()
                await self.job_manager.start()
                await self.task_manager.start()
                self.event_bridge.register()
                await self.scheduler.start()
                self.scheduler.add_job(
                    self._scheduled_health_check,
                    job_id="runtime-health",
                    trigger="interval",
                    seconds=60,
                )
                self.scheduler.add_job(
                    self._cleanup_runtime_metadata,
                    job_id="runtime-metadata-cleanup",
                    trigger="interval",
                    seconds=300,
                )
                self.scheduler.add_job(
                    self._run_internal_maintenance,
                    job_id="runtime-maintenance",
                    trigger="interval",
                    seconds=300,
                )
                self._started_at = datetime.now(UTC)
                self.lifecycle_manager.set_status(RuntimeStatus.RUNNING)
                await self.event_bus.publish_async(
                    Event(event_type="runtime.started", source="runtime")
                )
            except BaseException:
                self.lifecycle_manager.set_status(RuntimeStatus.FAILED)
                try:
                    await self.event_bus.publish_async(
                        Event(event_type="runtime.failed", source="runtime")
                    )
                    await self._cleanup()
                except BaseException:
                    logger.exception("Runtime startup rollback failed")
                raise

    async def _register_components(self) -> None:
        self.plugin_registry = PluginRegistry()
        self.plugin_loader = PluginLoader()
        self.plugin_manager = PluginManager(
            registry=self.plugin_registry,
            loader=self.plugin_loader,
            runtime=self,
        )
        components = {
            "runtime_context": self,
            "lifecycle_manager": self.lifecycle_manager,
            "state_manager": self.state_manager,
            "event_bus": self.event_bus,
            "task_manager": self.task_manager,
            "job_manager": self.job_manager,
            "scheduler": self.scheduler,
            "websocket_manager": self.websocket_manager,
            "plugin_registry": self.plugin_registry,
            "plugin_loader": self.plugin_loader,
            "plugin_manager": self.plugin_manager,
            "workflow_repository": self.workflow_repository,
            "execution_repository": self.execution_repository,
            "template_repository": self.template_repository,
            "workflow_validator": self.workflow_validator,
            "audit_trail": self.audit_trail,
            "workflow_service": self.services.workflow_service,
            "workflow_runner": self.services.workflow_runner,
            "execution_service": self.services.execution_service,
            "template_service": self.services.template_service,
        }
        for name, component in components.items():
            if not self.registry.exists(name):
                self.registry.register(name, component)
                await self.event_bus.publish_async(
                    Event(
                        event_type="component.registered",
                        source="runtime",
                        payload={"name": name},
                    )
                )

        await self.plugin_manager.load(
            "app.plugins.system.diagnostics.plugin"
        )

    async def stop(self) -> None:
        async with self._stop_lock:
            if self.lifecycle_manager.get_status() is RuntimeStatus.STOPPED:
                return
            self.lifecycle_manager.set_status(RuntimeStatus.STOPPING)
            self.job_manager.reject_new_jobs()
            await self.event_bus.publish_async(
                Event(event_type="runtime.stopping", source="runtime")
            )
            try:
                await self._cleanup(publish_stopped=True)
            except BaseException:
                self.lifecycle_manager.set_status(RuntimeStatus.FAILED)
                raise
            else:
                self.lifecycle_manager.set_status(RuntimeStatus.STOPPED)

    async def _cleanup(self, *, publish_stopped: bool = False) -> None:
        errors: list[BaseException] = []
        self.job_manager.reject_new_jobs()
        for cleanup in (
            self.scheduler.shutdown,
            self.task_manager.stop_all,
            self.job_manager.stop,
        ):
            try:
                await cleanup()
            except BaseException as exc:
                errors.append(exc)
        if publish_stopped:
            try:
                await self.event_bus.publish_async(
                    Event(event_type="runtime.stopped", source="runtime")
                )
            except BaseException as exc:
                errors.append(exc)
        self.event_bridge.unregister()
        for name in self.registry.list_components():
            try:
                await self.event_bus.publish_async(
                    Event(
                        event_type="component.unregistered",
                        source="runtime",
                        payload={"name": name},
                    )
                )
            except BaseException as exc:
                errors.append(exc)
        self.registry.clear()
        try:
            await self.event_bus.wait_for_handlers(timeout=1.0)
        except BaseException as exc:
            errors.append(exc)
        if errors:
            raise RuntimeError("Runtime cleanup failed") from errors[0]

    def _refresh_health(self) -> None:
        self._last_health_check = datetime.now(UTC)

    async def _scheduled_health_check(self) -> None:
        self._refresh_health()

    async def _cleanup_runtime_metadata(self) -> None:
        self.job_manager.cleanup_completed()

    async def _run_internal_maintenance(self) -> None:
        self.state_manager.set(
            "runtime:last_maintenance",
            datetime.now(UTC),
        )

    def get_health(self) -> RuntimeHealth:
        now = datetime.now(UTC)
        uptime = (
            max(0.0, (now - self._started_at).total_seconds())
            if self._started_at is not None
            else 0.0
        )
        jobs = self.job_manager.list_jobs()
        return RuntimeHealth(
            runtime_status=self.lifecycle_manager.get_status(),
            uptime=uptime,
            active_jobs=sum(
                job.status.value == "running" for job in jobs
            ),
            queued_jobs=sum(
                job.status.value == "queued" for job in jobs
            ),
            failed_jobs=sum(
                job.status.value in ("failed", "timed_out") for job in jobs
            ),
            registered_components=len(self.registry.list_components()),
            scheduler_status=self.scheduler.get_status(),
            last_health_check=self._last_health_check,
        )
