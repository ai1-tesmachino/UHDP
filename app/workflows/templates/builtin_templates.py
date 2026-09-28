from app.workflows.templates.cpu_validation_workflow import (
    create_cpu_validation_workflow,
)
from app.workflows.templates.memory_validation_workflow import (
    create_memory_validation_workflow,
)
from app.workflows.templates.network_validation_workflow import (
    create_network_validation_workflow,
)
from app.workflows.templates.storage_validation_workflow import (
    create_storage_validation_workflow,
)
from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)
from app.workflows.templates.template import (
    WorkflowTemplate,
)


def get_builtin_templates() -> list[
    WorkflowTemplate
]:
    return [
        WorkflowTemplate(
            name="cpu_validation_workflow",
            description="CPU diagnostic workflow",
            workflow=create_cpu_validation_workflow(),
        ),
        WorkflowTemplate(
            name="memory_validation_workflow",
            description="Memory diagnostic workflow",
            workflow=create_memory_validation_workflow(),
        ),
        WorkflowTemplate(
            name="storage_validation_workflow",
            description="Storage diagnostic workflow",
            workflow=create_storage_validation_workflow(),
        ),
        WorkflowTemplate(
            name="network_validation_workflow",
            description="Network diagnostic workflow",
            workflow=create_network_validation_workflow(),
        ),
        WorkflowTemplate(
            name="full_system_validation_workflow",
            description="Full system diagnostic workflow",
            workflow=create_full_system_validation_workflow(),
        ),
    ]