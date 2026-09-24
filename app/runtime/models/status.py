from enum import Enum


class RuntimeStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"