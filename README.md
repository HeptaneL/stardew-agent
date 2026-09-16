# Stardew Agent

An experimental Agent runtime that connects AI Agents with
[Stardew Valley](https://www.stardewvalley.net/) through MCP.

The goal is to explore how an Agent can perceive and reason about
a persistent game environment, rather than simply act as a chatbot.

It currently ships three agents and works together with the
[HelloStardew](https://github.com/HeptaneL/HelloStardew) SMAPI mod on the Steam
version of the game. Game state flows *into* the agent through MCP, and the
agent's replies flow back *into* the game.

## Agents

### CyberJu — the farm assistant

CyberJu is a tool-using agent. It reads the live game state through MCP tools
(calendar, events, birthdays, current date) before answering, so its advice is
grounded in what is actually happening on the farm.

- Graph: `src/stardew_agent/agents/butler.py`
- Prompt: `CYBERJU_PROMPTS` in `src/stardew_agent/prompts.py`, one per language
- In game: type `cj <message>` in the chat box to talk to it
- Style: concise, calm, slightly formal; 1–3 short points

<img width="1512" height="982" alt="Screenshot 2026-09-12 at 5 16 55 PM" src="https://github.com/user-attachments/assets/faab78a1-07a7-4616-9588-1b2b0d851a11" />


### Spouse — living dialogue

The Spouse agent replaces the farmer's spouse's scripted dialogue with something
generated on the spot. It keeps the character's personality, but is no longer
limited to the lines written for her.

It is a tool-using agent too, but on a shorter leash than CyberJu: it sees only
the lookups a person living in the valley would plausibly make — the date and
today's events, her household, how everyone stands with the farmer, where the
farmer is, and what the farmer has recently been doing. The calendar and
birthday tools stay with CyberJu, whose job is planning the day rather than
living it. The allowlist is `CHARACTER_TOOLS` in `src/stardew_agent/mcp_client.py`,
shared with the Villager agent below.

- Graph: `src/stardew_agent/agents/spouse.py`
- Prompt: assembled by `src/stardew_agent/persona.py` from a character document
  and a skill document
- In game: hold `Alt` and click your spouse, type what you want to say, and she
  answers with a few replies you can pick from
- Style: one or two natural sentences, no Markdown

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/21f76ce8-45a5-457c-b8f6-31d2affad136" />


### Villager — the same, for everyone else

The Villager agent does for every other villager what the Spouse agent does for
the farmer's spouse: replaces the scripted dialogue with something generated on
the spot, while keeping the character's personality and their actual standing
with the farmer.

It shares the Spouse agent's tool allowlist and its reply format. The only
difference between the two is the skill document in the system prompt, so a
character is written once and can be met either way.

Which of the two applies is the mod's decision, not the agent's: it sends
`is_spouse` on every request, because it is the side that can see whether the
farmer married this person, and the name alone cannot say.

- Graph: `src/stardew_agent/agents/villager.py`
- Prompt: `villager_prompt` in `src/stardew_agent/persona.py`, from a character
  document and `skills/villagers/SKILL.md`
- In game: hold `Alt` and click any villager
- Style: one or two natural sentences, no Markdown


## Personas

A prompt is assembled from three separate things. Keeping them apart is what
lets a skill apply to a different character later, and a character appear in
more than one mode.

| Layer | Lives in | Answers |
| --- | --- | --- |
| Character | `src/stardew_agent/assets/character/<name>.md` | who someone is — identity, interests, relationships |
| Skill | `src/stardew_agent/assets/skills/<skill>/SKILL.md` | how to behave in a mode, whoever you are |
| Format contract | `DIALOGUE_FORMAT_CONTRACTS` in `prompts.py` | how to emit the reply the mod parses |

They are joined character → skill → contract, so the output contract sits
closest to where generation starts.

Today there is one character, Haley (`character/haley.md`), and two skills she
can be paired with — `skills/spouse/SKILL.md` and `skills/villagers/SKILL.md`.
The pairing is chosen per request by `is_spouse`; see
[Villager](#villager--the-same-for-everyone-else).

These were seeded from the
[stardew-skills](https://github.com/HeptaneL/stardew-skills) repo, which is a
separate experimental space. The copies here are what actually runs, and they
are **not** kept in sync with it — edit them here.

### Still not wired up: memory

Game tools landed, so the spouse skill's `## Use of Context` now describes what
she can look up. Conversation memory did not, and it is a separate thing: the
tools report on the farm and the day, not on what the two of you said to each
other last week. The skill therefore still says plainly that she does not
remember earlier conversations.

`## Relationship Continuity` and the paragraph about not remembering in
`## Use of Context` are the sections to revisit when a memory store lands, in
`assets/skills/spouse/SKILL.md`.

### Adding a character

1. Add `src/stardew_agent/assets/character/<name>.md`, named after the NPC's
   internal name (lowercase). `Haley` is looked up as `haley.md`.
2. Talk to them in game — as the player's spouse, or as any villager.

No code change is needed — `POST /chat` resolves any name that has a document
and returns `404` for any that does not. Both skills already exist, so a new
character works in both modes as soon as their document does.

The one exception is a name the mod never sends because the NPC cannot be
talked to, where the request fails before it reaches here.

To add a language, put the translated document in a directory named after it,
beside the English original (`assets/character/zh/haley.md`). See
[Language](#language).

The markdown is read on every request, so edits take effect without a restart.

## Language

There is one prompt set per language, and nothing is translated. A message goes
to the agent in the language it was written, and the reply comes back in that
language because the prompt asked for it in that language:

```text
Chinese in ──► Chinese prompt ──► agent ──► Chinese out
  English in ──► English prompt ──► agent ──► English out
```

Send `"language": "zh"` and the Chinese set is used end to end: the CyberJu
prompt, the character document, the skill document, and the format contract.
Only the primary subtag matters, so `zh`, `zh-CN`, `zh-Hans` and `zh-TW` all
resolve to `zh`. Anything without a set of its own resolves to English, which is
also the default.

Writing the reply in Chinese directly, rather than in English and rendering it
afterwards, is the point. A character's voice is a property of the character,
and phrasing written for Chinese reads as that character rather than as a
faithful copy of someone else's sentence. It also makes a Chinese reply a
single model call.

Two things to know:

- A translated document is a sibling of the English one, under a directory named
  after the language (`assets/character/zh/haley.md`). Each document resolves
  independently and a missing translation falls back to English with a warning,
  so a character can ship in one language and be translated later.
- A thread's history is in whatever language it was written in. Switching
  language mid-thread does not rewrite the earlier turns, and the system prompt
  is only sent on the first turn of a thread, so a thread opened in English
  keeps answering in English. Start a new `thread_id` to change language.

The wire format is the one thing that does not change with the language. The mod
parses the reply by `- ` and `% `, so both prompt sets use the same ASCII
markers, and the Chinese contract says so explicitly — a model writing Chinese
would otherwise reach for the full-width `－` and `％`, which the mod would not
recognise.

The Chinese set was written against the Chinese localisation shipped with the
game and ValleyTalk's `i18n/zh.json`, so names and register match what a Chinese
player already reads in game — 鹈鹕镇 for Pelican Town, 农夫 for the farmer,
花舞节 for the Flower Dance. Keep that vocabulary when adding a Chinese
document; a prompt that calls the town 鹈鹕镇 and a character doc that calls it
something else reads as two different games.

The mod sets the language for the session and does not currently send it, so
this is reachable over `POST /chat` but not yet from in game.

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
  MCP server wraps as tools. All three agents call those tools — CyberJu all of
  them, the spouse and the villager a shared subset — to ground what they say in
  the actual farm.
- **Agent → Game:** the mod POSTs to the agent's `/chat` endpoint and writes the
  reply back into the game (chat box for CyberJu, dialogue box for the spouse
  and for villagers).

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
{
  "character": "Haley",
  "message": "今天下午你在做什么？",
  "thread_id": "haley-spring-12",
  "language": "zh",
  "is_spouse": true
}
```

| Field | Description |
| --- | --- |
| `character` | `CyberJu`, or the name of an NPC with a character document |
| `message` | What the player said |
| `thread_id` | The conversation this message belongs to; state is kept per thread |
| `language` | `en` (default) or `zh`; picks the prompt set, see [Language](#language) |
| `is_spouse` | Required. Whether that NPC is the farmer's spouse or roommate; picks the skill |

`character` is either `CyberJu` (the tool-using assistant) or the name of an
NPC with a character document, which is answered as the player's spouse when
`is_spouse` is true and as an ordinary villager when it is false.
The name is matched case-insensitively against
`src/stardew_agent/assets/character/`, and an unknown name returns `404`.

`is_spouse` has no default on purpose. Guessing `false` would answer the
farmer's own spouse in the villager persona, which reads as a slightly off
character rather than as a bug; a missing field fails with `422` instead.
`CyberJu` carries it too, but is matched by name first and ignores it.

Agents are cached per `(is_spouse, character)` pair, so the same villager met
as a spouse in one save and as a neighbour in another keeps two separate
histories.

The reply carries the same `character` and the answer in `message`. A spouse
answers in the dialogue format the mod parses:

```json
{
  "character": "Haley",
  "message": "- I spent most of the afternoon taking photos.\n% That sounds fun.\n% What did you take pictures of?\n% Tell me more."
}
```

The first line, starting with `- `, is what the character says. The lines
starting with `% ` are replies the player can pick from. CyberJu answers in
plain prose instead, since its reply goes to the chat box rather than the
dialogue box.

With `"language": "zh"` the same shape comes back in Chinese, because the same
contract was given in Chinese and the markers are ASCII in both:

```json
{
  "character": "Haley",
  "message": "- 今天下午我都在镇上拍照，光线特别好。\n% 拍的什么？\n% 听起来很有意思。\n% 下次带我一起去。"
}
```

## Project layout

```text
src/stardew_agent/
├── api.py            # FastAPI /chat dispatcher
├── agents/
│   ├── butler.py     # CyberJu — ReAct loop with all MCP tools
│   ├── spouse.py     # Spouse — ReAct loop with a subset of MCP tools
│   └── villager.py   # Villager — the same subset, a different skill
├── assets/
│   ├── character/    # who someone is, one file per NPC
│   │   └── zh/       #   ...and the same files, per language
│   └── skills/       # how to behave in a mode, one dir per mode
│       ├── spouse/zh/
│       └── villagers/zh/
├── persona.py        # loads character + skill, assembles the prompt
├── prompts.py        # CYBERJU_PROMPTS, DIALOGUE_FORMAT_CONTRACTS, per language
├── mcp_client.py     # MCP stdio client -> stardew-mcp-server
├── model.py          # LLM client
└── config.py         # .env settings
```
