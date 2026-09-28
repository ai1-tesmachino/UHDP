from app.workflows.actions.print_action import PrintAction
from app.workflows.persistence.file_repository import FileWorkflowRepository
from app.workflows.workflow import Workflow


def create_workflow(
    name: str = "test_workflow",
) -> Workflow:
    return Workflow(
        name=name,
        actions=[
            PrintAction(
                message="test",
            ),
        ],
    )


def test_save_workflow(tmp_path):

    repository = FileWorkflowRepository(
        tmp_path,
    )

    workflow = create_workflow()

    repository.save(
        workflow,
    )

    assert (
        tmp_path / f"{workflow.name}.json"
    ).exists()


def test_load_workflow(tmp_path):

    repository = FileWorkflowRepository(
        tmp_path,
    )

    workflow = create_workflow()

    repository.save(
        workflow,
    )

    loaded = repository.load(
        workflow.name,
    )

    assert loaded.name == workflow.name
    assert len(loaded.actions) == 1
    assert isinstance(
        loaded.actions[0],
        PrintAction,
    )
    assert loaded.actions[0].message == "test"


def test_delete_workflow(tmp_path):

    repository = FileWorkflowRepository(
        tmp_path,
    )

    workflow = create_workflow()

    repository.save(
        workflow,
    )

    assert repository.exists(
        workflow.name,
    )

    repository.delete(
        workflow.name,
    )

    assert not repository.exists(
        workflow.name,
    )


def test_list_workflows(tmp_path):

    repository = FileWorkflowRepository(
        tmp_path,
    )

    workflow_a = create_workflow(
        "workflow_a",
    )

    workflow_b = create_workflow(
        "workflow_b",
    )

    repository.save(
        workflow_a,
    )

    repository.save(
        workflow_b,
    )

    workflows = repository.list()

    assert workflows == [
        "workflow_a",
        "workflow_b",
    ]