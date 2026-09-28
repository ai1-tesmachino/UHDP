from app.workflows.workflow import (
    Workflow,
)

from app.workflows.templates.template import (
    WorkflowTemplate,
)

from app.workflows.templates.file_template_repository import (
    FileTemplateRepository,
)


def test_save_and_load(
    tmp_path,
):
    repository = (
        FileTemplateRepository(
            tmp_path
        )
    )

    template = WorkflowTemplate(
        name="backup",
        description="desc",
        workflow=Workflow(
            name="workflow",
            actions=[],
        ),
    )

    repository.save(
        template
    )

    loaded = repository.load(
        "backup"
    )

    assert (
        loaded.name
        == "backup"
    )

    assert (
        loaded.description
        == "desc"
    )


def test_exists(
    tmp_path,
):
    repository = (
        FileTemplateRepository(
            tmp_path
        )
    )

    template = WorkflowTemplate(
        name="backup",
        description="desc",
        workflow=Workflow(
            name="workflow",
             actions=[],
        ),
    )

    repository.save(
        template
    )

    assert repository.exists(
        "backup"
    )


def test_delete(
    tmp_path,
):
    repository = (
        FileTemplateRepository(
            tmp_path
        )
    )

    template = WorkflowTemplate(
        name="backup",
        description="desc",
        workflow=Workflow(
            name="workflow",
            actions=[],
        ),
    )

    repository.save(
        template
    )

    repository.delete(
        "backup"
    )

    assert not repository.exists(
        "backup"
    )


def test_list(
    tmp_path,
):
    repository = (
        FileTemplateRepository(
            tmp_path
        )
    )

    repository.save(
        WorkflowTemplate(
            name="a",
            description="a",
            workflow=Workflow(
                name="wa",
                actions=[],
            ),
        )
    )

    repository.save(
        WorkflowTemplate(
            name="b",
            description="b",
            workflow=Workflow(
                name="wb",
                actions=[],
            ),
        )
    )

    assert len(
        repository.list()
    ) == 2