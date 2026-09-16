from typing import Annotated, Literal
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict

from stardew_agent.model import llm
from stardew_agent.mcp_client import get_character_tools
import logging

logger = logging.getLogger(__name__)


class VillagerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def create_villager():
    """Build the graph that answers as a villager the farmer is not married to.

    Same ReAct shape as :func:`stardew_agent.agents.spouse.create_spouse` — the
    difference between the two modes is the skill document in the system prompt,
    not the graph. They are kept as separate factories so either one can grow a
    tool, a checkpointer, or a guard without dragging the other along.
    """
    tools = await get_character_tools()

    model = llm.bind_tools(tools=tools)

    async def call_model(state: VillagerState):
        response = await model.ainvoke(state["messages"])

        logger.info("LLM response: %r", response.content)
        return {"messages": [response]}

    def should_continue(state: VillagerState) -> Literal["tools", END]:
        last_message = state["messages"][-1]

        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(VillagerState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools=tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    checkpoint = InMemorySaver()

    return graph.compile(
        checkpointer=checkpoint
    )
