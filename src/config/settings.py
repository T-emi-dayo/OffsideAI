from pydantic_settings import BaseSettings
from pydantic import Field

class AppSettings(BaseSettings):
    app_name: str = Field(default="", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="0.1.0", env="VERSION")

    FOOTBALL_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    FOOTBALL_DATA_ORG_KEY: str = ""
        
    BASE_TEMPERATURE: float = 0.7
    BASE_MODEL: str = "gemini-2.5-flash"
    BASE_MODEL_PROVIDER: str = "google_genai"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = AppSettings()
