from enum import Enum


class WorkflowStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"