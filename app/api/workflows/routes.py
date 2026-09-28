from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from app.api.dependencies import get_runtime
from app.runtime.context import RuntimeContext

from app.workflows.persistence.default_serializers import (
    create_default_serializer,
)

router = APIRouter()

_serializer = create_default_serializer()

def get_workflow_service(
    runtime: RuntimeContext = Depends(get_runtime),
):
    return runtime.registry.get(
        "workflow_service"
    )


@router.post("/")
async def create_workflow(
    data: dict,
    service=Depends(get_workflow_service),
):
    try:
        workflow = _serializer.deserialize(data)

        service.save(workflow)

        return _serializer.serialize(workflow)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/")
async def list_workflows(
    service=Depends(get_workflow_service),
):
    return {
        "workflows": service.list(),
    }

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    runtime: RuntimeContext = Depends(get_runtime),
):
    workflow_service = runtime.registry.get(
        "workflow_service"
    )

    execution_service = runtime.registry.get(
        "execution_service"
    )

    try:
        workflow = workflow_service.get(
            workflow_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    result = await execution_service.execute(
        workflow
    )

    return asdict(result)


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    service=Depends(get_workflow_service),
):
    try:
        workflow = service.get(
            workflow_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return _serializer.serialize(
        workflow
    )


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    service=Depends(get_workflow_service),
):
    service.delete(
        workflow_id
    )

    return {
        "deleted": workflow_id,
    }