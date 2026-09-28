from app.workflows.workflow import (
    Workflow,
)

from app.workflows.persistence.file_repository import (
    FileWorkflowRepository,
)

from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)

from app.workflows.templates.template import (
    WorkflowTemplate,
)

from app.workflows.templates.file_template_repository import (
    FileTemplateRepository,
)

from app.workflows.actions.fail_action import (
    FailAction,
)

from app.workflows.actions.print_action import (
    PrintAction,
)

def test_workflow_lifecycle(
    tmp_path,
):
    workflow_repository = (
        FileWorkflowRepository(
            tmp_path / "workflows"
        )
    )

    execution_repository = (
        FileExecutionRepository(
            tmp_path / "executions"
        )
    )

    template_repository = (
        FileTemplateRepository(
            tmp_path / "templates"
        )
    )

    workflow = Workflow(
    name="backup",
    actions=[
        PrintAction(
            "hello"
        ),
    ],
    )

    workflow_repository.save(
        workflow
    )

    loaded_workflow = (
        workflow_repository.load(
            "backup"
        )
    )

    assert (
        loaded_workflow.name
        == "backup"
    )

    execution = ExecutionRecord(
        workflow_name="backup"
    )

    execution.mark_completed()

    execution_repository.save(
        execution
    )

    loaded_execution = (
        execution_repository.load(
            execution.execution_id
        )
    )

    assert (
        loaded_execution.workflow_name
        == "backup"
    )

    template = WorkflowTemplate(
        name="backup_template",
        description="backup",
        workflow=workflow,
    )

    template_repository.save(
        template
    )

    loaded_template = (
        template_repository.load(
            "backup_template"
        )
    )

    assert (
        loaded_template.name
        == "backup_template"
    )