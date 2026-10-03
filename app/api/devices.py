from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException

from app.discovery.discovery_service import (
    discovery_service,
)


router = APIRouter(
    prefix="/devices",
    tags=["devices"],
)


def device_to_dict(
    device,
) -> dict[str, Any]:

    return {
        "device_id": device.device_id,
        "device_type": device.device_type,
        "name": device.name,
        "properties": device.properties,
    }


@router.get("/")
def get_devices() -> list[dict[str, Any]]:

    result = discovery_service.discover()

    return [
        device_to_dict(device)
        for device in result.devices
    ]


@router.get("/{device_id}")
def get_device(
    device_id: str,
) -> dict[str, Any]:

    devices = discovery_service.discover()

    device = next(
        (
            device
            for device in devices.devices
            if device.device_id == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Device not found: {device_id}",
        )

    return device_to_dict(device)