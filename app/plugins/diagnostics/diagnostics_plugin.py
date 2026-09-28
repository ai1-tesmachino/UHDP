from app.plugins.base import BasePlugin
from app.plugins.diagnostics.event_history import EventHistory
from app.runtime.events.events_type import EventTypes


class DiagnosticsPlugin(BasePlugin):
    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.history = EventHistory()

    async def initialize(self):
        self.event_bus.subscribe_all(self.on_event)

    async def shutdown(self):
        pass

    def on_event(self, event):
        self.history.add(event)

    def get_event_count(self):
        return self.history.count()

    def get_recent_events(self, limit=10):
        return self.history.latest(limit)

    def clear_history(self):
        self.history.clear()

    def get_registered_events(self):
        return self.event_bus.registered_events()