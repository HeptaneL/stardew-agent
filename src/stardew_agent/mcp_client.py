from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from stardew_agent.config import settings

MCP_ROOT = Path(settings.stardew_mcp_path) / "stardew-mcp-server"

# A character is a person in the valley, not a farm assistant, so they get only
# the lookups they would plausibly make: their household, how they and the
# player stand with everyone, where the player is and what the day has been
# like. The calendar and birthday lookups stay with CyberJu, whose job is
# planning the day rather than living it.
#
# The spouse and an ordinary villager ask the same questions of the world, so
# they share one allowlist. Only the persona differs, and that lives in the
# skill document.
CHARACTER_TOOLS = frozenset(
    {
        "get_current_date",
        "get_todays_events",
        "get_household",
        "get_relationship",
        "get_current_state",
        "get_recent_activity",
    }
)

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

async def get_character_tools():
    """The subset of the server's tools a character persona may use."""
    tools = await get_tools()
    return [tool for tool in tools if tool.name in CHARACTER_TOOLS]

#if __name__ == "__main__":
#    import asyncio
#
#    async def main():
#        tools = await get_tools()
#        for tool in tools:
#            print(tool.name)
#
#    asyncio.run(main())
