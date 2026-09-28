from app.workflows.actions.base import Action
from app.workflows.actions.foreach import ForEachAction
from app.workflows.workflow_context import WorkflowContext


class CounterAction(Action):

    def __init__(self) -> None:
        self.count = 0

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        self.count += 1


class CaptureAction(Action):

    def __init__(self) -> None:
        self.values = []

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        self.values.append(
            (
                context.get("user"),
                context.get("index"),
                context.get("count"),
            )
        )


def test_foreach_iterates_all_items():

    context = WorkflowContext()

    context.set(
        "users",
        ["a", "b", "c"],
    )

    counter = CounterAction()

    action = ForEachAction(
        collection_name="users",
        item_name="user",
        actions=[counter],
    )

    action.execute(context)

    assert counter.count == 3


def test_foreach_empty_collection():

    context = WorkflowContext()

    context.set(
        "users",
        [],
    )

    counter = CounterAction()

    action = ForEachAction(
        collection_name="users",
        item_name="user",
        actions=[counter],
    )

    action.execute(context)

    assert counter.count == 0


def test_foreach_exposes_iteration_variables():

    context = WorkflowContext()

    context.set(
        "users",
        ["alice", "bob"],
    )

    capture = CaptureAction()

    action = ForEachAction(
        collection_name="users",
        item_name="user",
        actions=[capture],
    )

    action.execute(context)

    assert capture.values == [
        ("alice", 0, 2),
        ("bob", 1, 2),
    ]


def test_foreach_missing_collection_returns_empty():

    context = WorkflowContext()

    counter = CounterAction()

    action = ForEachAction(
        collection_name="users",
        item_name="user",
        actions=[counter],
    )

    action.execute(context)

    assert counter.count == 0