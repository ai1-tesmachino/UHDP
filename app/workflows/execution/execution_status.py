from enum import StrEnum


class ExecutionStatus(
    StrEnum,
):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"