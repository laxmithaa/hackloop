"""Database layer for the Healthcare Bill Navigator (PostgreSQL, psycopg 3)."""

from .access import (
    count_question,
    get_verified_record,
    issue_access_code,
    start_verification,
    submit_access_code,
)
from .callbacks import (
    InvalidTransition,
    create_callback_ticket,
    list_support_workers,
    list_tickets,
    set_case_summary,
    set_triage_final,
    update_ticket_status,
    withdraw_consent,
)
from .logs import checker_pass_rates, log_generated_text, record_consent
from .lookup import ScanComparison, compare_scanned_to_record, lookup_bill
from .pool import create_pool
from .settings import DbSettings, get_db_settings

__all__ = [
    "DbSettings",
    "InvalidTransition",
    "ScanComparison",
    "checker_pass_rates",
    "compare_scanned_to_record",
    "count_question",
    "create_callback_ticket",
    "create_pool",
    "get_db_settings",
    "get_verified_record",
    "issue_access_code",
    "list_support_workers",
    "list_tickets",
    "log_generated_text",
    "lookup_bill",
    "record_consent",
    "set_case_summary",
    "set_triage_final",
    "start_verification",
    "submit_access_code",
    "update_ticket_status",
    "withdraw_consent",
]
