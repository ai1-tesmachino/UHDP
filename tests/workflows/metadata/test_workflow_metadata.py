from app.workflows.metadata.workflow_metadata import (
    WorkflowMetadata,
)


def test_metadata_defaults():
    metadata = WorkflowMetadata()

    assert metadata.created_at is not None

    assert metadata.updated_at is not None

    assert metadata.version is not None


def test_touch_updates_timestamp():
    metadata = WorkflowMetadata()

    previous = metadata.updated_at

    metadata.touch()

    assert (
        metadata.updated_at
        >= previous
    )