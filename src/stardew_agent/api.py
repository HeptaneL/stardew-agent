from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from stardew_agent.agents.butler import create_butler

app = FastAPI()

class ChatRequest(BaseModel):
    character: str = "CyberJu"
    message: str

class ChatResponse(BaseModel):
    character: str
    message: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    agent = await create_butler()
    result = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(request.message)
            ]
        }
    )

    response = result["messages"][-1]

    return ChatResponse(
        character=request.character,
        message=response.content,
    )
