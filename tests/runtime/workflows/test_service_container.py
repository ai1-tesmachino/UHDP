from app.runtime.workflow.service_container import (
    ServiceContainer,
)


class FakeWorkflowRepository:
    def save(self, workflow):
        pass

    def load(self, workflow_id):
        return None

    def delete(self, workflow_id):
        pass

    def list(self):
        return []


class FakeExecutionRepository:

    def save(self, execution):
        pass

    def load(self, execution_id):
        return None

    def list(self):
        return []


class FakeTemplateRepository:

    def save(self, template):
        pass

    def load(self, template_id):
        return None

    def delete(self, template_id):
        pass

    def list(self):
        return []


def test_service_container_wires_services():

    container = ServiceContainer(
        workflow_repository=FakeWorkflowRepository(),
        execution_repository=FakeExecutionRepository(),
        template_repository=FakeTemplateRepository(),
    )

    assert container.workflow_service is not None
    assert container.workflow_runner is not None
    assert container.execution_service is not None
    assert container.template_service is not None

    assert (
        container.execution_service._runner
        is container.workflow_runner
    )