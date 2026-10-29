"""Integration-test fixtures.

These tests run against a REAL PostgreSQL database built by
`python -m app.db.setup --reset`. DATABASE_URL comes from the environment or
the .env file. They are skipped when it is not set, so `pytest` still works
without Postgres. Each test runs inside a transaction that is rolled back, so tests never leave
data behind.
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.db.pool import ensure_windows_async_compat
from app.db.settings import get_db_settings

# pytest-asyncio creates its loop from the current policy, so pick a selector
# loop before any test runs — psycopg's async driver cannot use Windows'
# default ProactorEventLoop.
ensure_windows_async_compat()

BILL_1 = "aaaaaaaa-0000-0000-0000-000000000001"  # INV-2026-0042, code DEMO-1234
BILL_2 = "aaaaaaaa-0000-0000-0000-000000000002"  # SMC/2026/118,  code DEMO-5678
BILL_3 = "aaaaaaaa-0000-0000-0000-000000000003"  # CC-0007 (fully settled)
BILL_4 = "aaaaaaaa-0000-0000-0000-000000000004"  # INV-2026-0100 (no insurance)

T0 = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def conn():
    url = get_db_settings().database_url  # environment variable or .env file
    if not url:
        pytest.skip("DATABASE_URL is not set")
    connection = await AsyncConnection.connect(url, row_factory=dict_row)
    try:
        yield connection
    finally:
        await connection.rollback()
        await connection.close()
