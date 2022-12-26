import os
from functools import lru_cache

from pydantic import BaseSettings, Field

if os.getenv("CQLENG_ALLOW_SCHEMA_MANAGEMENT") is None:
    os.environ["CQLENG_ALLOW_SCHEMA_MANAGEMENT"] = "1"

class Settings(BaseSettings):
    name: str = Field(..., env="PROJECT_NAME")
    db_clientid: str = Field(..., env='Astra_clientID')
    db_clientsecret: str = Field(..., env='Astra_clientSecret')
    redis_url: str = Field(..., env='REDIS_URL')

    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()