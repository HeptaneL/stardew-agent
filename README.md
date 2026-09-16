# Stardew Agent

An experimental Agent runtime that connects AI Agents with
[Stardew Valley](https://www.stardewvalley.net/) through MCP.

The goal is to explore how an Agent can perceive and reason about
a persistent game environment, rather than simply act as a chatbot.

It currently ships two agents and works together with the
[HelloStardew](https://github.com/HeptaneL/HelloStardew) SMAPI mod on the Steam
version of the game. Game state flows *into* the agent through MCP, and the
agent's replies flow back *into* the game.

## Agents

### CyberJu — the farm assistant

CyberJu is a tool-using agent. It reads the live game state through MCP tools
(calendar, events, birthdays, current date) before answering, so its advice is
grounded in what is actually happening on the farm.

- Graph: `src/stardew_agent/agents/butler.py`
- Prompt: `CYBERJU_PROMPT` in `src/stardew_agent/prompts.py`
- In game: type `cj <message>` in the chat box to talk to it
- Style: concise, calm, slightly formal; 1–3 short points

<img width="1512" height="982" alt="Screenshot 2026-09-12 at 5 16 55 PM" src="https://github.com/user-attachments/assets/faab78a1-07a7-4616-9588-1b2b0d851a11" />


### Spouse — living dialogue

The Spouse agent replaces the farmer's spouse's scripted dialogue with something
generated on the spot. It keeps the character's personality and memories, but is
no longer limited to the lines written for her.

- Graph: `src/stardew_agent/agents/spouse.py`
- Prompt: assembled by `src/stardew_agent/persona.py` from a character document
  and a skill document
- In game: hold `Alt` and click your spouse, type what you want to say, and she
  answers with a few replies you can pick from
- Style: one or two natural sentences, no Markdown

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/21f76ce8-45a5-457c-b8f6-31d2affad136" />


## Personas

A prompt is assembled from three separate things. Keeping them apart is what
lets a skill apply to a different character later, and a character appear in
more than one mode.

| Layer | Lives in | Answers |
| --- | --- | --- |
| Character | `src/stardew_agent/assets/character/<name>.md` | who someone is — identity, interests, relationships |
| Skill | `src/stardew_agent/assets/skills/<skill>/SKILL.md` | how to behave in a mode, whoever you are |
| Format contract | `DIALOGUE_FORMAT_CONTRACT` in `prompts.py` | how to emit the reply the mod parses |

They are joined character → skill → contract, so the output contract sits
closest to where generation starts.

Today the only pairing is Haley (`character/haley.md`) in the spouse mode
(`skills/spouse/SKILL.md`).

These were seeded from the
[stardew-skills](https://github.com/HeptaneL/stardew-skills) repo, which is a
separate experimental space. The copies here are what actually runs, and they
are **not** kept in sync with it — edit them here.

### Not wired up yet

The spouse skill used to describe looking things up through memory and game
tools. Neither exists on this path yet: `agents/spouse.py` binds no tools, and
there is no memory store. Rather than asking for capabilities that are not
there, the skill now states plainly that the character does not remember earlier
conversations and does not know what the player has been doing today.

When tools or memory do land, these are the sections to revisit:
`## Use of Context` and `## Relationship Continuity` in
`assets/skills/spouse/SKILL.md`.

### Adding a character

1. Add `src/stardew_agent/assets/character/<name>.md`, named after the NPC's
   internal name (lowercase). `Haley` is looked up as `haley.md`.
2. Talk to them in game as the player's spouse.

No code change is needed — `POST /chat` resolves any name that has a document
and returns `404` for any that does not.

The markdown is read on every request, so edits take effect without a restart.

## Architecture

```text
                    Stardew Valley
                         │
                       SMAPI
                         │
                  HelloStardew  ──────────────┐
                         │                    │
                    HTTP API                  │ POST /chat
                    :8788                     │ :8000
                         │                    │
                    MCP Server                │
                         │                    │
                       MCP                    │
                         │                    │
              ┌──────────▼──────────┐         │
              │    Stardew Agent    │         │
              │                     │         │
              │     LangGraph       │◄────────┘
              │     LangChain       │
              │        LLM          │
              └─────────────────────┘
```

Two directions:

- **Game → Agent:** the mod exposes the game state over an HTTP API, which the
  MCP server wraps as tools. CyberJu calls those tools to reason about the farm.
- **Agent → Game:** the mod POSTs to the agent's `/chat` endpoint and writes the
  reply back into the game (chat box for CyberJu, dialogue box for the spouse).

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Stardew Valley (Steam) with
  [SMAPI](https://smapi.io/) and
  [HelloStardew](https://github.com/HeptaneL/HelloStardew)
- The `stardew-mcp-server` (spawned automatically as an MCP stdio server)
- An OpenAI-compatible LLM API (DeepSeek by default)

## Configuration

Copy `.env.example` to `.env` and fill it in:

| Variable | Description |
| --- | --- |
| `MODEL` | Model name, e.g. `deepseek-flash` |
| `BASE_URL` | OpenAI-compatible base URL, e.g. `https://api.deepseek.com` |
| `OPENAI_API_KEY` | API key for the above |
| `STARDEW_MCP_PATH` | Directory containing `stardew-mcp-server` |
| `STARDEW_API_URL` | HelloStardew HTTP API, e.g. `http://127.0.0.1:8788` |

## Running

```bash
uv sync

# Start the agent API. The mod expects it on 127.0.0.1:8000.
uv run uvicorn stardew_agent.api:app --host 127.0.0.1 --port 8000
```

Then launch the game with the mod enabled:

- **CyberJu:** open the chat box and type `cj what should I do today?`
- **Spouse:** hold `Alt` and click your spouse, then type your message.

To check that the MCP server and mod connection work, run:

```bash
uv run python -m stardew_agent.test_mcp
```

## API

`POST http://127.0.0.1:8000/chat`

```json
{ "character": "CyberJu", "message": "what should I do today?" }
```

```json
{ "character": "Haley", "message": "..." }
```

`character` is either `CyberJu` (the tool-using assistant) or the name of an
NPC with a character document, which is answered as the player's spouse.
The name is matched case-insensitively against
`src/stardew_agent/assets/character/`, and an unknown name returns `404`.

## Project layout

```text
src/stardew_agent/
├── api.py            # FastAPI /chat dispatcher
├── agents/
│   ├── butler.py     # CyberJu — ReAct loop with MCP tools
│   └── spouse.py     # Spouse — single-node dialogue graph
├── assets/
│   ├── character/    # who someone is, one file per NPC
│   └── skills/       # how to behave in a mode, one dir per mode
├── persona.py        # loads character + skill, assembles the prompt
├── prompts.py        # CYBERJU_PROMPT, DIALOGUE_FORMAT_CONTRACT
├── mcp_client.py     # MCP stdio client -> stardew-mcp-server
├── model.py          # LLM client
└── config.py         # .env settings
```
