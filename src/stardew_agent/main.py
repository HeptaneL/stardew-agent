import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from stardew_agent.agents.butler import create_butler
from stardew_agent.prompts import SYSTEM_PROMPT

async def main():
    agent = await create_butler()

    result = await agent.ainvoke(
        {
            "messages":[
                SystemMessage(SYSTEM_PROMPT),
                HumanMessage("今天有什么重要的事情?")
            ]
        }
    )
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
