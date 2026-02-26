from __future__ import annotations

import base64


def safe_b64decode(data: str) -> bytes | None:
    """Decode a base64 payload that may or may not include a data-url prefix."""

    if not data:
        return None

    raw = data.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]

    try:
        return base64.b64decode(raw, validate=False)
    except Exception:
        return None
