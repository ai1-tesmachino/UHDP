from dataclasses import dataclass


@dataclass(slots=True)
class PluginMetadata:
    name: str
    version: str
    description: str