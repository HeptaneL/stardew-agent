from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from stardew_agent.agents.butler import create_butler
from stardew_agent.agents.spouse import create_spouse
from stardew_agent.persona import PersonaNotFound, spouse_prompt
from stardew_agent.prompts import CYBERJU_PROMPT
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


app = FastAPI()

spouse_agents = {}

class ChatRequest(BaseModel):
    character: str
    message: str
    thread_id: str

class ChatResponse(BaseModel):
    character: str
    message: str

async def get_spouse_agent(character: str):
    if character not in spouse_agents:
        spouse_agents[character] = await create_spouse()

    return spouse_agents[character]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.character == "CyberJu":
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
    # Not CyberJu, so treat the name as a character sheet and talk to them as
    # the player's spouse. Adding a character means adding one markdown file.
    try:
        system_prompt = spouse_prompt(request.character)
    except PersonaNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    agent = await get_spouse_agent(request.character)

    config = {
        "configurable": {
            "thread_id": request.thread_id,
        }
    }

    state = await agent.aget_state(config)

    if state.values:
        messages = [
            HumanMessage(request.message)
        ]
    else:
        messages = [
            SystemMessage(system_prompt),
            HumanMessage(request.message),
        ]

    result = await agent.ainvoke(
        {"messages": messages},
        config = config,
    )
    response = result["messages"][-1]
    content = format_spouse_reply(response.content)
    return ChatResponse(
        character=request.character,
        message=content,
    )

def sanitize_response(text: str) -> str:
    return text.replace("*", "")


def _strip_wrapping_quotes(text: str) -> str:
    return text.strip().strip('"').strip()


def format_spouse_reply(text: str) -> str:
    """
    Reduce the model's reply to the shape the mod parses: one "- " line for
    what the spouse says, followed by "% " lines for the farmer's options.

    Models routinely add a preamble, a code fence, bold markers, or quotes, so
    rather than trusting the output, rebuild it from the lines that actually
    carry the format. Falls back to the cleaned text when the model ignored the
    format entirely, so the farmer still sees something.
    """
    cleaned = sanitize_response(text).replace("`", "")

    line: str | None = None
    options: list[str] = []
    fallback: str | None = None

    for raw in cleaned.splitlines():
        current = raw.strip()
        if not current:
            continue

        if current.startswith("-"):
            # Only the first spoken line counts; the mod ignores any others.
            if line is None:
                line = _strip_wrapping_quotes(current.lstrip("-"))
            continue

        if current.startswith("%"):
            body = _strip_wrapping_quotes(current.lstrip("%"))
            if body:
                options.append(body)
            continue

        if line is not None:
            # An unmarked line while the spoken line is still open is a wrapped
            # sentence. Once options have started, unmarked lines are trailing
            # commentary and get dropped.
            if not options:
                line = f"{line} {current}"
        elif fallback is None:
            # An unmarked line before any marker is probably a preamble. Keep it
            # only as a last resort so a real "- " line can take precedence.
            fallback = current

    line = line or fallback
    if not line:
        return cleaned.strip()

    return "\n".join([f"- {line}", *(f"% {option}" for option in options)])
