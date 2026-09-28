from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class ForEachAction(Action):

    def __init__(
        self,
        collection_name: str,
        item_name: str,
        actions: list[Action],
    ) -> None:
        self.collection_name = collection_name
        self.item_name = item_name
        self.actions = actions

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        items = context.get(
            self.collection_name,
            [],
        )

        total = len(items)

        for index, item in enumerate(items):

            context.set(
                self.item_name,
                item,
            )

            context.set(
                "index",
                index,
            )

            context.set(
                "count",
                total,
            )

            for action in self.actions:
                action.execute(context)