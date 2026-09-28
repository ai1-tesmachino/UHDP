import pytest

from app.runtime.application import Application
from app.runtime.context import RuntimeContext


@pytest.mark.asyncio
async def test_runtime_wires_workflow_services(tmp_path):
    runtime = RuntimeContext(data_dir=tmp_path)
    application = Application(runtime=runtime)

    await application.start()

    try:
        assert runtime.registry.get(
            "workflow_repository"
        ) is runtime.workflow_repository

        assert runtime.registry.get(
            "execution_repository"
        ) is runtime.execution_repository

        assert runtime.registry.get(
            "template_repository"
        ) is runtime.template_repository

        assert runtime.registry.get(
            "workflow_validator"
        ) is runtime.workflow_validator

        assert runtime.registry.get(
            "audit_trail"
        ) is runtime.audit_trail

        assert runtime.registry.get(
            "workflow_service"
        ) is runtime.services.workflow_service

        assert runtime.registry.get(
            "workflow_runner"
        ) is runtime.services.workflow_runner

        assert runtime.registry.get(
            "execution_service"
        ) is runtime.services.execution_service

        assert runtime.registry.get(
            "template_service"
        ) is runtime.services.template_service

    finally:
        await application.stop()


def test_runtime_creates_workflow_data_directories(tmp_path):
    runtime = RuntimeContext(
        data_dir=tmp_path
    )

    assert (tmp_path / "workflows").exists()
    assert (tmp_path / "executions").exists()
    assert (tmp_path / "templates").exists()
