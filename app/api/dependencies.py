from fastapi import Request

from app.runtime.context import RuntimeContext
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.managers.state_manager import StateManager
from app.runtime.background.task_manager import TaskManager


def get_runtime(request: Request) -> RuntimeContext:
    return request.app.state.runtime


def get_state_manager(request: Request) -> StateManager:
    return get_runtime(request).state_manager


def get_event_bus(request: Request) -> EventBus:
    return get_runtime(request).event_bus


def get_task_manager(request: Request) -> TaskManager:
    return get_runtime(request).task_manager


def get_job_manager(request: Request) -> JobManager:
    return get_runtime(request).job_manager