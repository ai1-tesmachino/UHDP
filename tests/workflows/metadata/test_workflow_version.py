from app.workflows.metadata.workflow_version import (
    WorkflowVersion,
)


def test_default_version():
    version = WorkflowVersion()

    assert version.major == 1
    assert version.minor == 0
    assert version.patch == 0


def test_version_string():
    version = WorkflowVersion(
        major=2,
        minor=5,
        patch=9,
    )

    assert str(
        version
    ) == "2.5.9"