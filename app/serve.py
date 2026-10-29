"""Start the API with an event loop that async psycopg can use.

Uvicorn's CLI picks the loop itself and, on Windows, chooses
``ProactorEventLoop``. Async psycopg needs ``add_reader()``, which only the
selector loop provides, so the pool would time out on startup. Uvicorn offers
no CLI switch for this, so we build the server here and run ``serve()`` on a
selector loop instead.

Usage (from the repo root)::

    python -m app.serve            # 127.0.0.1:8000
    python -m app.serve --port 9000

Without ``DATABASE_URL`` the in-memory mode works under plain
``uvicorn app.main:app`` too; this runner is only required for PostgreSQL.
"""

from __future__ import annotations

import argparse
import asyncio

import uvicorn

from app.db.pool import ensure_windows_async_compat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Healthcare Bill Navigator API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Reload on code changes.")
    args = parser.parse_args(argv)

    ensure_windows_async_compat()
    config = uvicorn.Config(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
