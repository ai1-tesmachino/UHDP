from collections.abc import Callable

from .event import Event

EventHandler = Callable[[Event], None]