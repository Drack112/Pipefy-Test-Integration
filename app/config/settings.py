from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "teste-python"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str

    cors_allowed_origins: List[str] = ["*"]
    cors_allowed_headers: List[str] = ["*"]

    pipefy_api_url: str = "https://api.pipefy.com/graphql"
    pipefy_token: str = ""
    pipefy_pipe_id: str = ""


settings = Settings()
