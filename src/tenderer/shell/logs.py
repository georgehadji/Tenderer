"""Logs hold no personal data (docs/architecture.md §10.3): a filter on every handler replaces ΑΦΜ-like numbers,
phone numbers and e-mail addresses before a record is written. Audit events use ids instead (§6.7)."""

import logging
import re

_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[email]"),
    (re.compile(r"(?<![\w+])(\+30)?\d{10}(?!\d)"), "[phone]"),
    (re.compile(r"(?<!\d)\d{9}(?!\d)"), "[tax-id]"),
)


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactPersonalData(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = redact(record.getMessage()), ()
        if record.exc_info and not record.exc_text:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        return True
