"""Greek identifiers as value objects at the boundary: normalise, or raise ValueError (§6.4, §6.13)."""

import re

_LATIN_TO_GREEK = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")
_PLATE = re.compile(r"^([ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ]{3})(\d{4})$")


def afm(raw: str) -> str:
    """ΑΦΜ: 9 digits; the last is (Σ digit_i × 2^(8-i), i = 0..7) mod 11 mod 10."""
    value = raw.strip()
    if not re.fullmatch(r"\d{9}", value) or value == "000000000":
        raise ValueError("ΑΦΜ must be 9 digits")
    total = sum(int(d) << (8 - i) for i, d in enumerate(value[:8]))
    if total % 11 % 10 != int(value[8]):
        raise ValueError("ΑΦΜ check digit does not match")
    return value


def plate(raw: str) -> str:
    """Current format: three letters that exist in both alphabets, four digits, e.g. ΝΒΚ-1234. Latin look-alikes
    are converted. Older and special series are not accepted (UNVERIFIED which ones clients still use)."""
    compact = re.sub(r"[\s-]", "", raw).upper().translate(_LATIN_TO_GREEK)
    m = _PLATE.match(compact)
    if not m:
        raise ValueError("plate must look like ΑΒΓ-1234 with letters Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Υ Χ")
    return f"{m.group(1)}-{m.group(2)}"


def phone(raw: str) -> str:
    """Greek number in E.164: +30 and 10 digits starting with 2 (landline) or 69 (mobile)."""
    digits = re.sub(r"[\s().-]", "", raw)
    digits = re.sub(r"^(\+30|0030)", "", digits)
    if not re.fullmatch(r"(2\d{9}|69\d{8})", digits):
        raise ValueError("phone must be a Greek landline (2…) or mobile (69…) number with 10 digits")
    return "+30" + digits


VALIDATORS = {"tax_id": afm, "plate": plate, "phone": phone}
