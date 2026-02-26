from __future__ import annotations

from rag_healthbot_server.services.db.ReportRepo import (
    get_report_by_content_hash,
    get_report_by_extracted_text_hash,
)


def find_existing_report(*, content_hash: str | None, extracted_text_hash: str | None):
    """Return an existing Report matching hashes, or None."""

    existing = None
    if content_hash:
        existing = get_report_by_content_hash(content_hash)
    if existing is None and extracted_text_hash:
        existing = get_report_by_extracted_text_hash(extracted_text_hash)
    return existing
