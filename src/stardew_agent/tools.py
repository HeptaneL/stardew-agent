"""
Tools that read this project's own assets rather than the running game.

The MCP tools answer "what is happening in the valley right now"; these answer
"who is this person", from the same documents a persona prompt is built from.
They live here rather than in the MCP server because the server is a separate
process that has never seen ``assets/``, and because the documents ship with the
agent.

Nothing is cached, for the same reason ``persona.py`` caches nothing: editing a
document should take effect on the next request.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from stardew_agent.persona import (
    CHARACTER_DIR,
    PersonaNotFound,
    _strip_frontmatter,
    load_character,
)
from stardew_agent.prompts import DEFAULT_LANGUAGE, resolve_language

logger = logging.getLogger(__name__)


def _documents() -> list[Path]:
    """Every character document, translations included."""
    return sorted(CHARACTER_DIR.rglob("*.md"))


def _title(path: Path) -> str | None:
    """
    The name a document gives itself, taken from its first heading.

    The file name is the internal name (``evelyn.md``) while a translation names
    the character the way a player reads it (``# 艾芙琳``). Comparing headings as
    well as file names is what lets the farmer ask about someone by the name
    they actually know, without the model having to translate it first.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - the path was just listed
        return None

    for line in _strip_frontmatter(text).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            return stripped[2:].strip() or None
        return None

    return None


def _find(character: str) -> tuple[Path, str | None] | None:
    """
    The document for a name, and the language that name was written in.

    The file name is the canonical name, so it is tried first and needs no other
    document read. Only when that fails is every document opened to compare
    headings, which is what makes ``艾芙琳`` find ``evelyn.md``; the language that
    name came from is returned as a hint for a caller that named no language of
    its own.

    Matching against the documents that exist, rather than trusting the name, is
    also what keeps a name from walking out of ``assets/`` — the only paths this
    tool can ever read are the ones it listed itself.
    """
    wanted = " ".join((character or "").split()).casefold()
    if not wanted:
        return None

    documents = _documents()

    for path in documents:
        if path.parent == CHARACTER_DIR and path.stem.casefold() == wanted:
            return path, None

    for path in documents:
        if path.parent == CHARACTER_DIR:
            continue
        title = _title(path)
        if title and title.casefold() == wanted:
            # The original carries the content; the language is only a hint
            # about which copy to read.
            return CHARACTER_DIR / path.name, path.parent.name

    return None


def _unknown(character: str) -> str:
    """What the model gets back when a name matches no document."""
    names = sorted(
        path.stem for path in _documents() if path.parent == CHARACTER_DIR
    )
    return (
        f"No character profile for {character!r}. "
        f"Villagers with a profile: {', '.join(names)}. "
        "Check the spelling and call again with one of those names."
    )


@tool
def read_character_profile(
    character: Annotated[
        str,
        Field(description="Name of the villager, e.g. Evelyn or 艾芙琳."),
    ],
    language: Annotated[
        str,
        Field(
            description=(
                "Language of the profile: en or zh. Use the language the farmer "
                "is speaking; leave empty when unsure."
            )
        ),
    ] = "",
) -> str:
    """
    Read a villager's character profile: who they are, their interests, their
    relationships, and how they have changed.

    Call this before answering a question about a specific villager — who they
    are, what they are interested in, who they are close to — instead of
    guessing. The profile is background, not a script: use the part the question
    is about.

    This document does not hold the game's exact gift tastes. For what to give
    someone, use ``get_gift_tastes`` and ``suggest_gift`` instead.
    """
    found = _find(character)

    if found is None:
        logger.info("No character profile for %r", character)
        return _unknown(character)

    path, name_language = found

    # The farmer's own language wins. The language the name was written in is
    # only a fallback for a call that named none, so asking about 艾芙琳 still
    # reads the Chinese document without the model knowing it is filed under an
    # English name.
    chosen = (
        resolve_language(language)
        if language.strip()
        else resolve_language(name_language or DEFAULT_LANGUAGE)
    )

    try:
        return load_character(path.stem, chosen)
    except PersonaNotFound:  # pragma: no cover - the file was just listed
        return _unknown(character)


# The tools that come from this project rather than from the MCP server.
LOCAL_TOOLS = [read_character_profile]
