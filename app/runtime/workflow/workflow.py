from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True, init=False)
class Workflow:

    name: str
    actions: list
    workflow_id: str
    enabled: bool

    def __init__(
        self,
        name: str,
        actions: list,
    ) -> None:
        self.name = name
        self.actions = actions
        self.workflow_id = str(uuid4())
        self.enabled = True