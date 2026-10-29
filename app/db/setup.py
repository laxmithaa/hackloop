"""Create or reset the local database from the SQL files (one command).

Run from the backend/ folder:

    python -m app.db.setup --reset      # wipe, rebuild tables, load fictional data
    python -m app.db.setup              # apply the schema and data to an empty database
    python -m app.db.setup --no-seed    # schema only

--reset DELETES EVERYTHING in the database named by DATABASE_URL. It refuses to
run against a non-local host unless you add --allow-remote.
"""

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from .settings import get_db_settings

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "db" / "migrations" / "001_init.sql"
SEED = ROOT / "data" / "fictional" / "seed.sql"
LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set up the Navigator database.")
    parser.add_argument("--reset", action="store_true", help="wipe the database first")
    parser.add_argument("--no-seed", action="store_true", help="skip the fictional data")
    parser.add_argument(
        "--allow-remote", action="store_true", help="allow --reset on a non-local host"
    )
    args = parser.parse_args(argv)

    url = get_db_settings().database_url
    if not url:
        print("DATABASE_URL is not set. Put it in .env first.", file=sys.stderr)
        return 1

    host = conninfo_to_dict(url).get("host", "")
    if args.reset and host not in LOCAL_HOSTS and not args.allow_remote:
        print(
            f"Refusing to reset a non-local database ({host}). "
            "Add --allow-remote if you really mean it.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(url, autocommit=True) as conn:
            if args.reset:
                print("Resetting the database...")
                conn.execute(
                    """drop table if exists generated_texts, callback_tickets, support_workers,
                           consents, verification_sessions, access_codes, bill_financials,
                           bills, hospitals, languages cascade"""
                )
                conn.execute("drop function if exists set_updated_at() cascade")
            print(f"Applying {MIGRATION.relative_to(ROOT)}")
            conn.execute(MIGRATION.read_text(encoding="utf-8"))
            if not args.no_seed:
                print(f"Applying {SEED.relative_to(ROOT)}")
                conn.execute(SEED.read_text(encoding="utf-8"))
            count = conn.execute("select count(*) from bills").fetchone()[0]
    except psycopg.OperationalError:
        print(
            "Could not connect to the database. Check that PostgreSQL is running, "
            "that the database in DATABASE_URL exists, and that the password is right.",
            file=sys.stderr,
        )
        return 1
    except psycopg.errors.DuplicateTable:
        print(
            "The tables already exist. Run again with --reset to rebuild them "
            "(this deletes everything in the database).",
            file=sys.stderr,
        )
        return 1
    print(f"Done. {count} bills in the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
