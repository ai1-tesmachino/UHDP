from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5


_MISSING_VALUES = {
    "",
    "none",
    "null",
    "unknown",
    "not available",
    "n/a",
    "to be filled by o.e.m.",
    "default string",
}


@dataclass(slots=True)
class Asset:
    asset_id: str = field(default_factory=lambda: str(uuid4()))
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def add_discovered_identity(self, properties: dict[str, Any]) -> None:
        for field_name, keys in {
            "manufacturer": ("manufacturer", "Manufacturer", "vendor"),
            "model": ("model", "Model", "product"),
            "serial_number": ("serial_number", "SerialNumber", "serial"),
        }.items():
            if getattr(self, field_name) is not None:
                continue
            value = next(
                (
                    properties.get(key)
                    for key in keys
                    if _normalized(properties.get(key)) is not None
                ),
                None,
            )
            if value is not None:
                setattr(self, field_name, str(value).strip())


@dataclass(slots=True)
class HardwareComponent:
    component_id: str
    asset_id: str
    category: str
    identity_key: str
    legacy_device_id: str | None = None
    identity_basis: str = "provider_id"
    provisional: bool = True
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        asset_id: str,
        category: str,
        identity_key: str,
        legacy_device_id: str | None = None,
        identity_basis: str = "provider_id",
        properties: dict[str, Any] | None = None,
    ) -> HardwareComponent:
        stable_key = f"{category.strip().lower()}:{identity_key}"
        component_id = str(
            uuid5(NAMESPACE_URL, f"uhdp:{asset_id}:{stable_key}")
        )
        return cls(
            component_id=component_id,
            asset_id=asset_id,
            category=category,
            identity_key=stable_key,
            legacy_device_id=legacy_device_id,
            identity_basis=identity_basis,
            provisional=identity_basis not in {
                "serial_number",
                "world_wide_name",
            },
            properties=dict(properties or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def components_from_discovery(
    asset_id: str,
    devices: list[Any],
) -> list[HardwareComponent]:
    components: list[HardwareComponent] = []
    seen_keys: set[str] = set()
    discovered: list[tuple[int, str | None, str, dict[str, Any]]] = []
    identity_counts: dict[str, int] = {}
    provider_id_counts: dict[tuple[str, str], int] = {}

    for index, device in enumerate(devices):
        device_id = _value(device, "device_id")
        category = _value(device, "device_type")
        properties = _value(device, "properties")
        if (
            not isinstance(category, str)
            or not category
            or not isinstance(properties, dict)
            or category == "storage_inventory"
        ):
            continue
        if not isinstance(device_id, str) or not device_id.strip():
            device_id = None
        discovered.append((index, device_id, category, properties))
        if category != "system" and device_id is not None:
            identity_key, _ = _component_identity(category, device_id, properties)
            category_identity = f"{category.strip().lower()}:{identity_key}"
            identity_counts[category_identity] = (
                identity_counts.get(category_identity, 0) + 1
            )
            provider_key = (category, device_id.strip().lower())
            provider_id_counts[provider_key] = (
                provider_id_counts.get(provider_key, 0) + 1
            )

    for index, device_id, category, properties in discovered:
        if category != "system":
            if device_id is None:
                key, basis = f"reported_index:{index}", "reported_index"
            else:
                key, basis = _component_identity(category, device_id, properties)
                category_identity = f"{category.strip().lower()}:{key}"
                if identity_counts[category_identity] > 1:
                    provider_key = (category, device_id.strip().lower())
                    if provider_id_counts[provider_key] == 1:
                        key, basis = f"provider_id:{provider_key[1]}", "provider_id"
                    else:
                        key, basis = f"reported_index:{index}", "reported_index"
            component = HardwareComponent.create(
                asset_id=asset_id,
                category=category,
                identity_key=key,
                legacy_device_id=device_id,
                identity_basis=basis,
                properties=properties,
            )
            if component.identity_key not in seen_keys:
                components.append(component)
                seen_keys.add(component.identity_key)

        if category == "memory":
            modules = properties.get("memory_modules")
            if isinstance(modules, list):
                components.extend(
                    _memory_components(asset_id, device_id, modules, seen_keys)
                )

    return components


def component_for_device(
    components: list[dict[str, Any]],
    device_id: str,
) -> str | None:
    matches = [
        item
        for item in components
        if item.get("legacy_device_id") == device_id
        and item.get("category") != "memory_module"
        and isinstance(item.get("component_id"), str)
    ]
    return matches[0]["component_id"] if len(matches) == 1 else None


def _memory_components(
    asset_id: str,
    device_id: str | None,
    modules: list[Any],
    seen_keys: set[str],
) -> list[HardwareComponent]:
    valid_modules = [item for item in modules if isinstance(item, dict)]
    serial_counts: dict[str, int] = {}
    bank_counts: dict[str, int] = {}
    for module in valid_modules:
        serial = _first_normalized(module, ("serial_number", "SerialNumber", "serial"))
        bank = _first_normalized(module, ("bank", "BankLabel", "slot", "locator"))
        if serial:
            serial_counts[serial] = serial_counts.get(serial, 0) + 1
        if bank:
            bank_counts[bank] = bank_counts.get(bank, 0) + 1

    components: list[HardwareComponent] = []
    for index, module in enumerate(valid_modules):
        serial = _first_normalized(module, ("serial_number", "SerialNumber", "serial"))
        bank = _first_normalized(module, ("bank", "BankLabel", "slot", "locator"))
        if serial and serial_counts[serial] == 1:
            identity_key, basis = f"serial:{serial}", "serial_number"
        elif bank and bank_counts[bank] == 1:
            identity_key, basis = f"slot:{bank}", "slot"
        else:
            identity_key, basis = f"reported-index:{index}", "reported_index"
        component = HardwareComponent.create(
            asset_id=asset_id,
            category="memory_module",
            identity_key=identity_key,
            legacy_device_id=device_id,
            identity_basis=basis,
            properties=module,
        )
        if component.identity_key not in seen_keys:
            components.append(component)
            seen_keys.add(component.identity_key)
    return components


def _component_identity(
    category: str,
    device_id: str,
    properties: dict[str, Any],
) -> tuple[str, str]:
    for identity_field, keys in (
        ("serial_number", ("serial_number", "SerialNumber", "serial")),
        ("world_wide_name", ("wwn", "WWN", "world_wide_name", "eui")),
        ("pci_address", ("pci_address", "pci_slot", "bus_info", "pci_bus_id")),
    ):
        value = _first_normalized(properties, keys)
        if value:
            return f"{identity_field}:{value}", identity_field

    if category == "storage":
        value = _first_normalized(properties, ("device", "device_path", "path"))
        if value:
            return f"device_path:{value}", "device_path"

    return f"provider_id:{device_id.strip().lower()}", "provider_id"


def _first_normalized(
    values: dict[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = _normalized(values.get(key))
        if value is not None:
            return value
    return None


def _normalized(value: Any) -> str | None:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    normalized = " ".join(str(value).strip().lower().split())
    return None if normalized in _MISSING_VALUES else normalized


def _value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
