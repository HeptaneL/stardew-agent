from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model: str
    base_url: str
    openai_api_key: str
    stardew_mcp_path: str
    stardew_api_url: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
