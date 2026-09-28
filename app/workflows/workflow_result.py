from app.workflows.workflow_status import WorkflowStatus


class WorkflowResult:

    def __init__(
        self,
        status: WorkflowStatus,
        message: str = "",
    ) -> None:
        self.status = status
        self.message = message

    @property
    def success(self) -> bool:
        return self.status == WorkflowStatus.SUCCESS