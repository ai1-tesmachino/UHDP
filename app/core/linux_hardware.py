from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LINUX_POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")


def read_sysfs_value(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def linux_battery_inventory(
    root: Path = LINUX_POWER_SUPPLY_ROOT,
) -> tuple[dict[str, Any], str | None]:
    batteries = []
    if not root.exists():
        return {
            "battery_present": False,
            "batteries": [],
            "battery_count": 0,
            "inventory_status": "not_detected",
            "inventory_source": "sysfs",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }, None

    try:
        entries = sorted(root.iterdir())
    except OSError as exc:
        return {
            "battery_present": None,
            "batteries": [],
            "battery_count": 0,
            "inventory_status": "inaccessible",
            "inventory_source": "sysfs",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }, str(exc)

    for entry in entries:
        if read_sysfs_value(entry / "type") != "Battery":
            continue
        item: dict[str, Any] = {"name": entry.name, "source": "sysfs"}
        for field, filename in (
            ("manufacturer", "manufacturer"),
            ("model", "model_name"),
            ("serial_number", "serial_number"),
            ("status", "status"),
            ("capacity_percent", "capacity"),
        ):
            value = read_sysfs_value(entry / filename)
            if value is not None:
                if field == "capacity_percent":
                    try:
                        capacity = int(value)
                    except ValueError:
                        continue
                    if 0 <= capacity <= 100:
                        item[field] = capacity
                else:
                    item[field] = value
        for field, filename in (
            ("energy_full_design_uwh", "energy_full_design"),
            ("energy_full_uwh", "energy_full"),
            ("energy_now_uwh", "energy_now"),
            ("charge_full_design_uah", "charge_full_design"),
            ("charge_full_uah", "charge_full"),
            ("charge_now_uah", "charge_now"),
            ("cycle_count", "cycle_count"),
            ("voltage_now_uv", "voltage_now"),
            ("current_now_ua", "current_now"),
            ("power_now_uw", "power_now"),
        ):
            value = read_sysfs_value(entry / filename)
            if value is not None:
                try:
                    parsed_value = int(value)
                except ValueError:
                    item[field] = value
                else:
                    if parsed_value >= 0:
                        item[field] = parsed_value

        design = item.get("energy_full_design_uwh")
        full = item.get("energy_full_uwh")
        if isinstance(design, int) and design > 0 and isinstance(full, int):
            if 0 <= full <= design:
                item["wear_percent"] = round((design - full) / design * 100, 2)
                item["wear_calculation"] = (
                    "100 * (energy_full_design_uwh - energy_full_uwh) "
                    "/ energy_full_design_uwh"
                )
        batteries.append(item)

    mains = []
    for entry in entries:
        if read_sysfs_value(entry / "type") != "Mains":
            continue
        online = read_sysfs_value(entry / "online")
        mains.append({
            "name": entry.name,
            "online": int(online) if online in {"0", "1"} else None,
            "source": "sysfs",
        })

    return {
        "battery_present": bool(batteries),
        "batteries": batteries,
        "battery_count": len(batteries),
        "external_power": mains,
        "inventory_status": "detected" if batteries else "not_detected",
        "inventory_source": "sysfs",
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }, None
