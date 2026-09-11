# Stardew Agent

An experimental Agent runtime that connects AI Agents with
[Stardew Valley](https://www.stardewvalley.net/) through MCP.

The goal is to explore how an Agent can perceive and reason about
a persistent game environment, rather than simply act as a chatbot.

## Architecture

```text
                    Stardew Valley
                         │
                       SMAPI
                         │
                  HelloStardew
                         │
                    HTTP API
                         │
                    MCP Server
                         │
                       MCP
                         │
              ┌──────────▼──────────┐
              │    Stardew Agent    │
              │                     │
              │     LangGraph       │
              │     LangChain       │
              │        LLM          │
              └─────────────────────┘
