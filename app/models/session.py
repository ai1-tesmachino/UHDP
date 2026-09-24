from pydantic import BaseModel
from datetime import datetime

class Session(BaseModel):
    id:str
    created_at:datetime
    active:bool=True
