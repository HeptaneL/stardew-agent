from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from stardew_agent.agents.butler import create_butler
from stardew_agent.agents.spouse import create_spouse
from stardew_agent.agents.villager import create_villager
from stardew_agent.persona import (
    PersonaNotFound,
    bulter_prompt,
    spouse_prompt,
    villager_prompt,
)
from stardew_agent.prompts import CYBERJU_PROMPTS, resolve_language
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI()

# The two ways a named character can be met. Which one applies is the mod's call,
# not ours: it is the side that can see whether the farmer married this person,
# and the name alone cannot say.
SPOUSE = "spouse"
VILLAGER = "villager"
BULTER = "bulter"

_PROMPTS = {SPOUSE: spouse_prompt, VILLAGER: villager_prompt, BULTER: bulter_prompt}
_AGENT_FACTORIES = {SPOUSE: create_spouse, VILLAGER: create_villager, BULTER: create_butler}

# One graph per (mode, character), so the same villager talked to as a spouse in
# one save and as a neighbour in another keeps two separate histories. Each graph
# carries its own checkpointer, which is what makes that separation hold.
character_agents = {}

class ChatRequest(BaseModel):
    character: str
    message: str
    thread_id: str
    language: str = "en"
    # Not defaulted: a request that does not say which mode it wants would be
    # answered as a villager, and the farmer's own spouse would slide into the
    # wrong persona without anything looking wrong. Better a 422.
    is_spouse: bool

class ChatResponse(BaseModel):
    character: str
    message: str

async def get_character_agent(kind: str, character: str):
    key = (kind, character)

    if key not in character_agents:
        character_agents[key] = await _AGENT_FACTORIES[kind]()

    return character_agents[key]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # The language picks a prompt set, and the message goes to the agent as it
    # was written. Nothing is translated: a Chinese prompt is what makes the
    # reply Chinese, so the character's voice is written once rather than
    # written in English and rendered again.
    logger.info("LLM request: %r", request)
    language = resolve_language(request.language)
    config = {
        "configurable": {
            "thread_id": request.thread_id,
        }
    }

    if request.character == "CyberJu":
        kind = BULTER
    else:
        kind = SPOUSE if request.is_spouse else VILLAGER

    try:
        system_prompt = _PROMPTS[kind](request.character, language)
    except PersonaNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    agent = await get_character_agent(kind, request.character)

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
    content = format_dialogue_reply(response.content)

    return ChatResponse(
        character=request.character,
        message=content,
    )

def sanitize_response(orignal_text: str) -> str:
    text = orignal_text.replace("*", "") 
    text = text.replace("%","%")
    return text


# Both the ASCII pairs and the ones a Chinese reply is likely to arrive in. The
# prompt asks for no quotation marks at all, but a model that wraps the line
# anyway should not have the quotes land in the dialogue box.
_QUOTE_PAIRS = {'"': '"', "'": "'", "“": "”", "‘": "’", "「": "」", "『": "』"}


def _strip_wrapping_quotes(text: str) -> str:
    stripped = text.strip()
    while len(stripped) >= 2 and _QUOTE_PAIRS.get(stripped[0]) == stripped[-1]:
        stripped = stripped[1:-1].strip()
    return stripped


def format_dialogue_reply(text: str) -> str:
    """
    Reduce the model's reply to the shape the mod parses: one "- " line for
    what the character says, followed by "% " lines for the farmer's options.

    Shared by both modes: the wire format is the mod's, not the persona's.

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
