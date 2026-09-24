from pydantic import BaseModel


class PluginMetadata(BaseModel):
    name: str
    version: str
    description: str = ""
    author: str = ""