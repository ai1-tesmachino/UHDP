from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus


def listener(event):
    print(
        f"EVENT RECEIVED -> {event.event_type}"
    )


def main():
    bus = EventBus()

    bus.subscribe(
        "demo.event",
        listener,
    )

    bus.publish(
        Event(
            event_type="demo.event",
            source="demo",
        )
    )


if __name__ == "__main__":
    main()