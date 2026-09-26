"""Shared Postgres checkpointer for the LangGraph agents.

One pool + one saver is created per process and reused by every compiled graph.
Graphs stay isolated because the API folds ``(kind, character)`` into each
request's ``thread_id``, so the same ``thread_id`` never bleeds across modes or
characters even though they share the database.
"""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from stardew_agent.config import settings

_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the process-wide checkpointer, creating and migrating it once."""
    global _checkpointer

    if _checkpointer is None:
        async with _checkpointer_lock:
            if _checkpointer is None:
                pool = AsyncConnectionPool(
                    settings.database_url,
                    min_size=1,
                    max_size=10,
                    open=False,
                    kwargs={
                        "autocommit": True,
                        "prepare_threshold": 0,
                        "row_factory": dict_row,
                    },
                )
                # wait=True makes startup fail fast when Postgres is unreachable
                # instead of lazily timing out on the first checkpoint read/write.
                await pool.open(wait=True)
                saver = AsyncPostgresSaver(pool)
                await saver.setup()
                _checkpointer = saver

    return _checkpointer
