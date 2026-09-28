from __future__ import annotations

from app.runtime.workflow.execution_service import (
    ExecutionService,
)

from app.runtime.workflow.template_service import (
    TemplateService,
)

from app.runtime.workflow.workflow_runner import (
    WorkflowRunner,
)

from app.runtime.workflow.workflow_service import (
    WorkflowService,
)


class ServiceContainer:

    def __init__(
        self,
        workflow_repository,
        execution_repository,
        template_repository,
        validator=None,
        runner=None,
        audit_trail=None,
    ) -> None:

        self.workflow_service = WorkflowService(
            workflow_repository=workflow_repository,
            validator=validator,
        )

        self.workflow_runner = (
            runner
            or WorkflowRunner()
        )

        self.execution_service = ExecutionService(
            execution_repository=execution_repository,
            runner=self.workflow_runner,
            audit_trail=audit_trail,
        )

        self.template_service = TemplateService(
            template_repository=template_repository,
        )