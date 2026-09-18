from typing import Annotated, Literal
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from stardew_agent.model import llm
from stardew_agent.mcp_client import get_tools
from stardew_agent.tools import LOCAL_TOOLS
import logging

logger = logging.getLogger(__name__)


class ButlerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def create_butler():
    # The MCP tools report the valley as it is right now — including the gift
    # tools, which read the game's own taste data rather than a document. The
    # local tool reads the documents that ship with the agent, so CyberJu gets
    # both: the state and the person.
    tools = [*await get_tools(), *LOCAL_TOOLS]

    model = llm.bind_tools(tools=tools)

    async def call_model(state: ButlerState):
        response = await model.ainvoke(state["messages"])
    
        logger.info("LLM response: %r", response.content)
        return {"messages": [response]}

    def should_continue(state: ButlerState) -> Literal["tools", END]:
        last_message = state["messages"][-1]

        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(ButlerState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools=tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    checkpoint = InMemorySaver()

    return graph.compile(
        checkpointer = checkpoint
    )

