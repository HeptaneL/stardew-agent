import asyncio

from .mcp_client import get_tools


async def main():
    tools = await get_tools()

    print("TOOLS:")
    for tool in tools:
        print(tool.name)

    tool = next(
        tool for tool in tools
        if tool.name == "get_current_date"
    )

    print("\nCALL TOOL:")
    result = await tool.ainvoke({})

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
