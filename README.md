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

<!-- TODO: insert your screenshot below -->
![CyberJu in game](docs/screenshots/cyberju.png)

### Spouse — living dialogue

The Spouse agent replaces the farmer's spouse's scripted dialogue with something
generated on the spot. It keeps the character's personality and memories, but is
no longer limited to the lines written for her.

- Graph: `src/stardew_agent/agents/spouse.py`
- Prompt: `HALEY_PROMPT` in `src/stardew_agent/prompts.py`
- In game: walk up to your spouse and talk to her — the dialogue is generated live
- Style: one or two natural sentences, no Markdown

<!-- TODO: insert your screenshot below -->
![Spouse dialogue](docs/screenshots/spouse.png)

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
- **Spouse:** talk to your spouse and read the generated dialogue.

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
{ "character": "CyberJu", "message": "..." }
```

`character` is `CyberJu` (tool-using assistant) or `Haley` (spouse dialogue).
Any other value is rejected.

## Project layout

```text
src/stardew_agent/
├── api.py            # FastAPI /chat dispatcher
├── agents/
│   ├── butler.py     # CyberJu — ReAct loop with MCP tools
│   └── spouse.py     # Spouse — single-node dialogue graph
├── prompts.py        # CYBERJU_PROMPT, HALEY_PROMPT
├── mcp_client.py     # MCP stdio client -> stardew-mcp-server
├── model.py          # LLM client
└── config.py         # .env settings
```
