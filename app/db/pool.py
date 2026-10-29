"""Async PostgreSQL pool helpers for FastAPI."""

from __future__ import annotations

import asyncio
import sys
import warnings
from collections.abc import AsyncIterator

from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def ensure_windows_async_compat() -> None:
    """Make async psycopg usable on Windows before the event loop exists.

    psycopg's async driver relies on ``loop.add_reader()``, which Windows'
    default ``ProactorEventLoop`` does not provide, so connecting raises
    ``InterfaceError``. The selector loop does implement it.

    Must be called during application construction (before uvicorn calls
    ``asyncio.run``), not from inside the lifespan. No-op off Windows.
    """

    if sys.platform != "win32":
        return
    with warnings.catch_warnings():
        # The policy API is deprecated in Python 3.14 and removed in 3.16, but
        # on Windows it is still the only supported way to ask asyncio for a
        # selector loop — and psycopg's async driver cannot run without one.
        # The warning is suppressed because this repo turns DeprecationWarning
        # raised from app.* into test errors. Revisit when Python 3.16 lands:
        # at that point psycopg or a sync driver is the only option.
        warnings.simplefilter("ignore", DeprecationWarning)
        if isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy):
            return
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def create_pool(database_url: str) -> AsyncConnectionPool:
    """Build (but do not open) the async pool for application lifespan startup."""
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return AsyncConnectionPool(
        database_url,
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=5,
        open=False,
    )


async def get_db_connection(request: Request) -> AsyncIterator:
    """Yield a request-scoped connection; psycopg commits/rolls back on exit."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise RuntimeError("The database pool is not enabled")
    async with pool.connection() as connection:
        yield connection
