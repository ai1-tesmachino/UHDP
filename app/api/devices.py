from typing import Any

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.discovery.discovery_service import (
    discovery_service,
)
from app.persistence.local.database import SQLiteDatabase


router = APIRouter(
    prefix="/devices",
    tags=["devices"],
)

class InventoryFieldRequest(BaseModel):
    value: Any = None
    source: Literal["detected", "entered", "corrected"]
    verified: bool = False


class StationInventoryRequest(BaseModel):
    fields: dict[str, InventoryFieldRequest] = Field(default_factory=dict)
    notes: dict[str, str] = Field(default_factory=dict)
    custom_components: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


def device_to_dict(
    device,
) -> dict[str, Any]:

    return {
        "device_id": device.device_id,
        "device_type": device.device_type,
        "name": device.name,
        "properties": device.properties,
    }

@router.get("/inventory")
def get_station_inventory() -> dict[str, Any]:
    return SQLiteDatabase().get_station_inventory("local_station") or {
        "fields": {},
        "notes": {},
        "custom_components": [],
        "updated_at": None,
    }


@router.put("/inventory")
def save_station_inventory(
    request: StationInventoryRequest,
) -> dict[str, Any]:
    if len(request.fields) > 5000 or len(request.notes) > 200:
        raise HTTPException(status_code=400, detail="Inventory contains too many fields.")
    if any(len(note) > 4000 for note in request.notes.values()):
        raise HTTPException(status_code=400, detail="Inventory notes are limited to 4000 characters.")
    return SQLiteDatabase().save_station_inventory(
        "local_station",
        request.model_dump(),
    )


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