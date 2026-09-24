from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME:str="UHDP"
    APP_VERSION:str="1.0.0"
    HOST:str="0.0.0.0"
    PORT:int=8000
    LOG_LEVEL:str="INFO"
    SESSION_TIMEOUT_MINUTES:int=60

    class Config:
        env_file=".env"

@lru_cache
def get_settings():
    return Settings()
