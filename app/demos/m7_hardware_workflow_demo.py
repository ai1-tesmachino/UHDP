from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)
from app.workflows.workflow_context import WorkflowContext
from app.workflows.workflow_engine import WorkflowEngine
from app.workflows.workflow_status import WorkflowStatus


def main() -> None:
    workflow = create_full_system_validation_workflow()
    context = WorkflowContext()
    engine = WorkflowEngine()

    print("=" * 70)
    print("UHDP M7 - REAL HARDWARE FULL SYSTEM VALIDATION")
    print("=" * 70)
    print()

    result = engine.execute(
        workflow,
        context,
    )

    print(f"Workflow: {workflow.name}")
    print(f"Workflow Status: {result.status}")

    if result.message:
        print(f"Workflow Message: {result.message}")

    print()
    print("Diagnostic Results")
    print("-" * 70)

    diagnostic_keys = [
        "cpu_result",
        "memory_result",
        "storage_result",
        "network_result",
    ]

    for key in diagnostic_keys:
        diagnostic_result = context.get(key)

        if diagnostic_result is None:
            print(f"{key}: NOT EXECUTED")
            continue

        print(f"{key}:")
        print(f"  Diagnostic Type : {diagnostic_result.diagnostic_type}")
        print(f"  Device ID       : {diagnostic_result.device_id}")
        print(f"  Status          : {diagnostic_result.status}")
        print(f"  Message         : {diagnostic_result.message}")

        if diagnostic_result.details:
            print(f"  Details         : {diagnostic_result.details}")

        print()

    print("=" * 70)

    if result.status == WorkflowStatus.SUCCESS:
        print("M7 HARDWARE SMOKE TEST: PASSED")
    else:
        print("M7 HARDWARE SMOKE TEST: FAILED")

    print("=" * 70)


if __name__ == "__main__":
    main()