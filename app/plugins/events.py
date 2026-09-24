from pydantic import BaseModel


class PluginEvent(BaseModel):
    name: str
    description: str = ""