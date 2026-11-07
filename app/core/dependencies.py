from app.services.session_service import session_service

from fastapi import HTTPException, Request, status

from app.runtime.background.task_manager import TaskManager
from app.runtime.context import RuntimeContext
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.managers.state_manager import StateManager
from app.runtime.registry import RuntimeRegistry
from app.runtime.scheduler.async_scheduler import RuntimeScheduler


def get_session_service():
    return session_service


def get_runtime(request: Request) -> RuntimeContext:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application runtime is unavailable",
        )
    return runtime


def get_registry(request: Request) -> RuntimeRegistry:
    return get_runtime(request).registry


def get_state_manager(request: Request) -> StateManager:
    return get_runtime(request).state_manager


def get_event_bus(request: Request) -> EventBus:
    return get_runtime(request).event_bus


def get_job_manager(request: Request) -> JobManager:
    return get_runtime(request).job_manager


def get_task_manager(request: Request) -> TaskManager:
    return get_runtime(request).task_manager


def get_scheduler(request: Request) -> RuntimeScheduler:
    return get_runtime(request).scheduler
