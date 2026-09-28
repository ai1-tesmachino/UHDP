# app/workflows/workflow.py

class Workflow:

    def __init__(
        self,
        name: str,
        actions: list,
    ) -> None:
        self.name = name
        self.actions = actions