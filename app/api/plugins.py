from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request

router = APIRouter(
    prefix="/plugins",
    tags=["plugins"],
)


@router.get("/")
async def list_plugins(
    request: Request,
):
    manager = request.app.state.runtime.plugin_manager

    return [
        plugin.metadata.model_dump()
        for plugin in manager.list()
    ]


@router.post(
    "/{plugin_name}/services/{service_name}"
)
async def execute_service(
    plugin_name: str,
    service_name: str,
    request: Request,
):
    manager = request.app.state.runtime.plugin_manager

    try:
        service = manager.get_service(
            plugin_name,
            service_name,
        )

        return await service.execute()

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )