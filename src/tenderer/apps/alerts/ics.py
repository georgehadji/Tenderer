"""Calendar file (RFC 5545) for one all-day deadline, so the date lives in the client's own calendar even if our
system is down (S5). Pure: no Django, no clock. Sent as an attachment, never as a feed URL (§6.5)."""

from datetime import UTC, date, datetime, timedelta

# The event starts at 00:00 on the due day; these offsets ring at 09:00 three days and one day before it.
ALARMS = ("-P2DT15H", "-PT15H")


def calendar(uid: str, day: date, summary: str, description: str, stamp: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tenderer//alerts//EL", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp.astimezone(UTC):%Y%m%dT%H%M%SZ}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_text(summary)}",
        f"DESCRIPTION:{_text(description)}",
        "TRANSP:TRANSPARENT",
    ]
    for trigger in ALARMS:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"TRIGGER:{trigger}", f"DESCRIPTION:{_text(summary)}",
                  "END:VALARM"]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "".join(_fold(line) + "\r\n" for line in lines)


def _text(value: str) -> str:
    """TEXT escaping of RFC 5545 §3.3.11."""
    return (value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", ""))


def _fold(line: str) -> str:
    """Lines of at most 75 octets (§3.1), never splitting a UTF-8 character; continuation lines start with a space."""
    chunks, current, size, limit = [], "", 0, 75
    for ch in line:
        n = len(ch.encode())
        if size + n > limit:
            chunks.append(current)
            current, size, limit = "", 0, 74
        current += ch
        size += n
    chunks.append(current)
    return "\r\n ".join(chunks)
