"""Access-code provisioning for the fictional demo bills.

The codes themselves are *provided by the local developer* through
environment configuration and are never committed to source control:

    HBN_BILL_ACCESS_CODE_SUN2026004512=DEMO1234

(the suffix is the canonical, alphanumeric-only bill number; see
``normalise_bill_number``).

Design:
- The final state holds **only** a PBKDF2-HMAC-SHA256 digest with a unique
  per-bill random salt — the plain code is hashed once at startup and then
  dropped.
- Verification re-derives the digest from the submitted code and compares it
  in constant time (``hmac.compare_digest``).
- No bill has a default code and no endpoint ever returns a code; if a code
  is not configured, verification of that bill simply fails (never bypasses).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.services.records import normalise_bill_number

logger = logging.getLogger(__name__)

#: Environment prefix for per-bill demo codes, e.g.
#: ``HBN_BILL_ACCESS_CODE_SUN2026004512=...``.
PROVISIONING_ENV_PREFIX = "HBN_BILL_ACCESS_CODE_"

_SALT_BYTES = 16

_BILL_SUFFIX = re.compile(r"^[A-Z0-9]{4,32}$")


@dataclass(frozen=True)
class AccessCodeRecord:
    """Protected form of one bill's access code. Never contains the code."""

    salt: bytes
    digest: bytes
    iterations: int


def hash_access_code(code: str, *, iterations: int, salt: bytes | None = None) -> AccessCodeRecord:
    """Derive a PBKDF2 digest; ``salt`` exists for deterministic tests."""

    salt_bytes = salt if salt is not None else secrets.token_bytes(_SALT_BYTES)
    return AccessCodeRecord(
        salt=salt_bytes,
        digest=hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt_bytes, iterations),
        iterations=iterations,
    )


def verify_access_code(submitted: str, record: AccessCodeRecord) -> bool:
    """Constant-time digest comparison; never reveals why a code fails."""

    candidate = hashlib.pbkdf2_hmac(
        "sha256", submitted.encode("utf-8"), record.salt, record.iterations
    )
    return hmac.compare_digest(candidate, record.digest)


def parse_codes_from_env_file(env_file_text: str) -> dict[str, str]:
    """Extract ``HBN_BILL_ACCESS_CODE_*`` entries from a dotenv-style file.

    Only literal ``KEY=VALUE`` lines with the provisioning prefix are read;
    comments, blanks and all other keys are ignored. Plain values are kept in
    memory for hashing only and never logged.
    """

    codes: dict[str, str] = {}
    for raw_line in env_file_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key.upper().startswith(PROVISIONING_ENV_PREFIX):
            continue
        value = value.strip()
        # Tolerate simple quoting used in env files.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            codes[key.strip().upper()[len(PROVISIONING_ENV_PREFIX) :]] = value
    return codes


def collect_provisioned_codes(
    *,
    environ: Mapping[str, str],
    backend_dir: Path,
    records,
    iterations: int,
) -> dict[str, AccessCodeRecord]:
    """Build the digest map (``bill_id -> AccessCodeRecord``) from configuration.

    Sources: real environment variables first, then the local (git-ignored)
    ``.env`` file, which only fills what the environment does not set. Unknown
    bill suffixes and unusable entries are ignored with a warning: provisioning
    may never weaken verification.
    """

    raw_codes: dict[str, str] = {}
    for key, value in environ.items():
        upper = key.upper()
        if not upper.startswith(PROVISIONING_ENV_PREFIX):
            continue
        suffix = upper[len(PROVISIONING_ENV_PREFIX) :]
        if value.strip():
            raw_codes[suffix] = value.strip()
    env_file = backend_dir / ".env"
    if env_file.is_file():
        for suffix, value in parse_codes_from_env_file(
            env_file.read_text(encoding="utf-8")
        ).items():
            raw_codes.setdefault(suffix, value)

    digests: dict[str, AccessCodeRecord] = {}
    for suffix, plain_code in raw_codes.items():
        if not _BILL_SUFFIX.fullmatch(suffix.upper()):
            logger.warning("ignoring access-code entry with unusable bill suffix")
            continue
        normalised = normalise_bill_number(suffix)
        bills = records.find_bills_anywhere(normalised)
        if not bills:
            logger.warning("access-code entry does not match a registered fictional bill; ignored")
            continue
        if len(bills) > 1:  # pragma: no cover - registry has unique bill numbers
            logger.warning("ambiguity in access-code provisioning; entry ignored")
            continue
        # A fresh random salt per entry/bill startup keeps digests unique.
        digests[bills[0].bill_id] = hash_access_code(
            plain_code, iterations=iterations, salt=secrets.token_bytes(_SALT_BYTES)
        )
    return digests
