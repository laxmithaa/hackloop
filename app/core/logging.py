"""Application logging and request-scoped correlation IDs.

The request id is stored in a :class:`contextvars.ContextVar` so that any log
record emitted while handling a request carries the same correlation id, even
from deep inside service or route code.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar, Token

REQUEST_ID_PLACEHOLDER = "-"
LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_request_id: ContextVar[str] = ContextVar("request_id", default=REQUEST_ID_PLACEHOLDER)


def get_request_id() -> str:
    """Return the correlation id of the request being handled, if any."""

    return _request_id.get()


def set_request_id(value: str) -> Token[str]:
    """Bind ``value`` to the current context and return a reset token."""

    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    """Restore the previous correlation id."""

    _request_id.reset(token)


class RequestIdFilter(logging.Filter):
    """Make sure every record exposes a ``request_id`` attribute."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO", *, force: bool = False) -> None:
    """Configure root logging for the API process.

    Calling this repeatedly (for example in tests) replaces the handler instead
    of stacking duplicates.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=force,
    )
