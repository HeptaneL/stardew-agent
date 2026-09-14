from typing import Annotated
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from stardew_agent.model import llm
import logging

logger = logging.getLogger(__name__)

class SpouseState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def create_spouse():
    model = llm

    async def call_model(state: SpouseState):
        response = await model.ainvoke(state["messages"])

        logger.info("LLM response: %r", response.content)
        return {"messages": [response]}

    graph = StateGraph(SpouseState)
    graph.add_node("agent", call_model)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)

    return graph.compile()
