from app.workflows.action_registry import ActionRegistry


def test_register_action():

    registry = ActionRegistry()

    action = object()

    registry.register(
        "test",
        action,
    )

    assert registry.exists("test")


def test_get_action():

    registry = ActionRegistry()

    action = object()

    registry.register(
        "test",
        action,
    )

    assert registry.get("test") is action


def test_all_actions():

    registry = ActionRegistry()

    action = object()

    registry.register(
        "test",
        action,
    )

    actions = registry.all()

    assert "test" in actions