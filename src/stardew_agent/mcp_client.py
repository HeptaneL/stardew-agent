from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from stardew_agent.config import settings

MCP_ROOT = Path(settings.stardew_mcp_path) / "stardew-mcp-server"

client = MultiServerMCPClient(
    {
        "stardew": {
            "transport": "stdio",
            "command": str(MCP_ROOT/".venv/bin/python"),
            "args": [
                str(MCP_ROOT/"src/stardew_mcp_server/server.py"),
            ],
            "env": {
                "STARDEW_API_URL": settings.stardew_api_url,
                # The MCP SDK spawns the server with *only* this dict (it does
                # not inherit the parent environment), so any NO_PROXY from the
                # shell is lost. Without it httpx picks up the macOS system
                # proxy and routes the local request through it, which answers
                # HTTP 503. Keep localhost traffic direct.
                "NO_PROXY": "localhost,127.0.0.1,::1",
                "no_proxy": "localhost,127.0.0.1,::1",
            },
        },
    }
)

async def get_tools():
    return await client.get_tools()

#if __name__ == "__main__":
#    import asyncio
#
#    async def main():
#        tools = await get_tools()
#        for tool in tools:
#            print(tool.name)
#
#    asyncio.run(main())
