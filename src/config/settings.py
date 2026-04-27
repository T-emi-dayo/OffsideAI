from pydantic_settings import BaseSettings
from pydantic import Field


class LLMSettings(BaseSettings):
    provider: str = Field(default="", env="LLM_PROVIDER")
    api_key: str = Field(default="", env="LLM_API_KEY")
    model: str = Field(default="", env="LLM_MODEL")

    class Config:
        env_file = ".env"


class AppSettings(BaseSettings):
    app_name: str = Field(default="", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="0.1.0", env="VERSION")

    llm: LLMSettings = LLMSettings()

    # TODO: add project-specific setting groups here

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = AppSettings()
