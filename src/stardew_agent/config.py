from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model: str
    base_url: str
    openai_api_key: str
    # Path to the checkout that contains stardew-mcp-server. Only used by the
    # stdio transport; an HTTP deployment does not need it.
    stardew_mcp_path: str = ""
    stardew_api_url: str = "http://127.0.0.1:8788"
    database_url: str

    # ``stdio`` keeps the local-dev behaviour (the agent spawns the MCP server
    # as a subprocess). ``http`` / ``streamable-http`` connects to an MCP server
    # that is already running and exposing its Streamable HTTP endpoint.
    stardew_mcp_transport: str = "stdio"
    stardew_mcp_url: str = "http://127.0.0.1:8001/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
