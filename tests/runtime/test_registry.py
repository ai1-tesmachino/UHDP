from app.runtime.registry import RuntimeRegistry


def test_register_service():
    registry = RuntimeRegistry()

    service = object()

    registry.register(
        "test_service",
        service,
    )

    assert registry.exists("test_service")
    assert registry.get("test_service") is service


def test_unregister_service():
    registry = RuntimeRegistry()

    service = object()

    registry.register(
        "test_service",
        service,
    )

    registry.unregister("test_service")

    assert not registry.exists("test_service")


def test_duplicate_registration():
    registry = RuntimeRegistry()

    registry.register(
        "service",
        object(),
    )

    try:
        registry.register(
            "service",
            object(),
        )
        assert False
    except ValueError:
        assert True


def test_missing_service():
    registry = RuntimeRegistry()

    try:
        registry.get("missing")
        assert False
    except KeyError:
        assert True