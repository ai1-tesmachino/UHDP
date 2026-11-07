from collections.abc import Awaitable, Callable
from typing import Any

from .event import Event

EventHandler = Callable[[Event], Any | Awaitable[Any]]