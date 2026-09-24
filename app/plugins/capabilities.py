from enum import StrEnum


class PluginCapability(StrEnum):
    DIAGNOSTICS = "diagnostics"
    MONITORING = "monitoring"
    INVENTORY = "inventory"
    MAINTENANCE = "maintenance"