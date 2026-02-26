from __future__ import annotations

import hashlib

from .base64_utils import safe_b64decode


def md5_hex(payload: bytes) -> str:
    return hashlib.md5(payload).hexdigest()


def report_content_hash(file_content_b64: str) -> str | None:
    decoded = safe_b64decode(file_content_b64)
    if decoded is None:
        return None
    return md5_hex(decoded)


def extracted_text_hash(extracted_text: str) -> str:
    # Keep algorithm aligned with Postgres built-in `md5(text)` backfill.
    return md5_hex((extracted_text or "").encode("utf-8"))
