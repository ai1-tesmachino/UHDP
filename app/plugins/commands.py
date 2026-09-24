from pydantic import BaseModel


class PluginCommand(BaseModel):
    name: str
    description: str = ""