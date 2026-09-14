from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from stardew_agent.agents.butler import create_butler
from stardew_agent.prompts import CYBERJU_PROMPT
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


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
                SystemMessage(CYBERJU_PROMPT),
                HumanMessage(request.message)
            ]
        }
    )

    response = result["messages"][-1]
    content = sanitize_response(response.content)

    return ChatResponse(
        character=request.character,
        message=content,
    )

def sanitize_response(text: str) -> str:
    return text.replace("*", "")
