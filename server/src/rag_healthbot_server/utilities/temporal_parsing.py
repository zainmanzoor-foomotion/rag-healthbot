from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re


_NUMBER_WORDS: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

_RELATIVE_AGO_RE = re.compile(
    r"^(?P<amount>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?P<unit>day|week|month|year)s?\s+ago$"
)
_RELATIVE_IN_RE = re.compile(
    r"^in\s+(?P<amount>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?P<unit>day|week|month|year)s?$"
)
_RELATIVE_LAST_NEXT_RE = re.compile(
    r"^(?P<dir>last|next)\s+(?P<unit>day|week|month|year)$"
)


def _coerce_amount(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    return _NUMBER_WORDS.get(value)


def _unit_delta(unit: str, amount: int) -> timedelta:
    if unit == "day":
        return timedelta(days=amount)
    if unit == "week":
        return timedelta(weeks=amount)
    if unit == "month":
        return timedelta(days=30 * amount)
    return timedelta(days=365 * amount)


def _parse_relative_datetime(value: str, reference: datetime) -> datetime | None:
    lowered = value.strip().lower()
    if not lowered:
        return None

    if lowered in {"today", "now"}:
        return reference
    if lowered == "yesterday":
        return reference - timedelta(days=1)
    if lowered == "tomorrow":
        return reference + timedelta(days=1)

    ago_match = _RELATIVE_AGO_RE.match(lowered)
    if ago_match:
        amount = _coerce_amount(ago_match.group("amount"))
        unit = ago_match.group("unit")
        if amount is None:
            return None
        return reference - _unit_delta(unit, amount)

    in_match = _RELATIVE_IN_RE.match(lowered)
    if in_match:
        amount = _coerce_amount(in_match.group("amount"))
        unit = in_match.group("unit")
        if amount is None:
            return None
        return reference + _unit_delta(unit, amount)

    last_next_match = _RELATIVE_LAST_NEXT_RE.match(lowered)
    if last_next_match:
        direction = -1 if last_next_match.group("dir") == "last" else 1
        unit = last_next_match.group("unit")
        return reference + (direction * _unit_delta(unit, 1))

    return None


def _parse_absolute_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None

    normalized = cleaned.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    try:
        parsed_date = date.fromisoformat(cleaned)
        return datetime.combine(parsed_date, time.min)
    except ValueError:
        pass

    for fmt in ("%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if fmt == "%Y-%m":
                return datetime(parsed.year, parsed.month, 1)
            if fmt == "%Y":
                return datetime(parsed.year, 1, 1)
            return parsed
        except ValueError:
            continue

    return None


def parse_reference_datetime(value: str | datetime | date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    return _parse_absolute_datetime(value)


def normalize_temporal_value(
    value: str | datetime | date | None,
    *,
    reference_datetime: datetime,
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)

    absolute = _parse_absolute_datetime(value)
    if absolute is not None:
        return absolute

    return _parse_relative_datetime(value, reference_datetime)
