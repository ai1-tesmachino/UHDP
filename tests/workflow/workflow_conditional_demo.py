from app.workflows.workflow import Workflow

from app.workflows.actions.print_action import PrintAction
from app.workflows.actions.set_variable_action import (
    SetVariableAction,
)
from app.workflows.actions.conditional_action import (
    ConditionalAction,
)

from app.workflows.conditions.greater_than_condition import (
    GreaterThanCondition,
)

from app.workflows.workflow_engine import WorkflowEngine


workflow = Workflow(
    name="conditional_demo",
    actions=[
        SetVariableAction(
            "temperature",
            35,
        ),
        ConditionalAction(
            condition=GreaterThanCondition(
                "temperature",
                30,
            ),
            true_actions=[
                PrintAction(
                    "Hot weather",
                ),
            ],
            false_actions=[
                PrintAction(
                    "Cool weather",
                ),
            ],
        ),
    ],
)

engine = WorkflowEngine()

engine.execute(workflow)