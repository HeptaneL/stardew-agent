from typing import Annotated, Literal
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from stardew_agent.model import llm
from stardew_agent.mcp_client import get_tools

class ButlerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def create_butler():
    tools = await get_tools()

    model = llm.bind_tools(tools=tools)

    async def call_model(state: ButlerState):
        #print("\n======= MESSAGES ========")
        #for message in state["messages"]:
        #    print(message)
        #    print()
        response = await model.ainvoke(state["messages"])
        #print("MODEL RESPONSE")
        #print(response)
        #print("TOOL CALLS:")
        #print(response.tool_calls)
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

    return graph.compile()
