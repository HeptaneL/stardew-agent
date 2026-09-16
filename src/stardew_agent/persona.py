"""
Assembles the system prompt for an in-game character.

Two documents are combined, and they are deliberately separate things:

* a **character** document (``assets/character/<name>.md``) says who someone
  is — identity, interests, relationships, how they have changed.
* a **skill** document (``assets/skills/<skill>/SKILL.md``) says how to behave
  in a particular mode, independent of who the character is.

Keeping them apart is what lets one skill apply to a different character later,
and lets one character show up in different modes.

The wire format the mod parses is a third concern, owned by neither document,
and is passed in by the caller.

Nothing is cached, so editing a document takes effect on the next request
without restarting the server.
"""

from __future__ import annotations

from pathlib import Path

from stardew_agent.prompts import DIALOGUE_FORMAT_CONTRACT

ASSETS_ROOT = Path(__file__).parent / "assets"
CHARACTER_DIR = ASSETS_ROOT / "character"
SKILL_DIR = ASSETS_ROOT / "skills"

SPOUSE_SKILL = "spouse"


class PersonaNotFound(LookupError):
    """Raised when a character or skill document is missing."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PersonaNotFound(f"No persona document at {path}") from exc


def _strip_frontmatter(text: str) -> str:
    """
    Drop a leading ``---`` metadata block.

    Skill documents carry discovery metadata (``name``, ``description``) that
    is meant for tooling rather than for the model. Only one in-repo document
    uses it, and its closing fence is longer than three dashes, so match any
    line of three or more dashes rather than exactly ``---``.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text

    for index in range(1, len(lines)):
        fence = lines[index].strip()
        if len(fence) >= 3 and set(fence) == {"-"}:
            return "\n".join(lines[index + 1 :]).lstrip("\n")

    return text


def load_character(name: str) -> str:
    """Read the character document for ``name``. Matching is case-insensitive."""
    return _strip_frontmatter(_read(CHARACTER_DIR / f"{name.lower()}.md")).strip()


def load_skill(skill: str) -> str:
    """Read the skill document for ``skill``."""
    return _strip_frontmatter(_read(SKILL_DIR / skill / "SKILL.md")).strip()


def build_system_prompt(*, character: str, skill: str, contract: str) -> str:
    """
    Join the pieces into one prompt, most binding last so the output contract
    sits closest to where generation starts.
    """
    parts = (character, skill, contract)
    return "\n\n".join(part.strip() for part in parts if part.strip())


def spouse_prompt(character_name: str) -> str:
    """System prompt for talking to ``character_name`` as the player's spouse."""
    return build_system_prompt(
        character=load_character(character_name),
        skill=load_skill(SPOUSE_SKILL),
        contract=DIALOGUE_FORMAT_CONTRACT,
    )
