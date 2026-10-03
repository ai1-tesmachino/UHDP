from app.hal.default_diagnostics import (
    create_default_registry,
)


def test_default_registry_contains_cpu():
    registry = create_default_registry()

    assert registry.exists(
        "cpu"
    )


def test_default_registry_contains_memory():
    registry = create_default_registry()

    assert registry.exists(
        "memory"
    )


def test_default_registry_contains_storage():
    registry = create_default_registry()

    assert registry.exists(
        "storage"
    )


def test_default_registry_list():
    registry = create_default_registry()

    diagnostics = (
        registry.list_diagnostics()
    )

    assert diagnostics == [
        "battery",
        "bluetooth",
        "cpu",
        "display",
        "hdmi",
        "keyboard",
        "memory",
        "network",
        "speaker",
        "storage",
        "system",
        "usb",
        "usb_c",
        "vga",
        "webcam",
        "wifi",
    ]