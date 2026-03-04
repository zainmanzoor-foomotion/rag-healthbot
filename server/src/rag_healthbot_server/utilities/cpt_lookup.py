"""Local CPT code validation and name-based search.

Loads a CPT code file (CSV: ``code,label``) and provides:

* **Validation** – is a CPT code real?
* **Name search** – find codes by procedure description (word-overlap scoring)

Call :func:`set_cpt_file` at application startup.
"""

from __future__ import annotations

import csv
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_CPT_FILE: Path | None = None


# ── Startup configuration ─────────────────────────────────────────


def set_cpt_file(path: str | Path) -> None:
    """Set the path to the CPT code file.  Clears the cache."""
    global _CPT_FILE
    _CPT_FILE = Path(path)
    _load_cpt_data.cache_clear()
    logger.info("CPT file set to: %s", _CPT_FILE)


# ── Data loading (cached) ─────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_cpt_data() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return ``(code_to_desc, word_index)``."""
    code_to_desc: dict[str, str] = {}
    word_index: dict[str, list[str]] = {}

    if _CPT_FILE is None or not _CPT_FILE.exists():
        logger.warning("CPT file not configured or missing: %s", _CPT_FILE)
        return code_to_desc, word_index

    logger.info("Loading CPT codes from %s …", _CPT_FILE)
    count = 0

    with open(_CPT_FILE, encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)  # skip header row

        # Detect if the first row is actually data (no header)
        if header and re.match(r"^\d{4,5}", header[0]):
            # No real header — treat as data
            if len(header) >= 2:
                code, desc = header[0].strip(), header[1].strip()
                code_to_desc[code] = desc
                count += 1
                for w in set(re.findall(r"[a-z]{3,}", desc.lower())):
                    word_index.setdefault(w, []).append(code)

        for row in reader:
            if len(row) < 2:
                continue
            code = row[0].strip()
            desc = row[1].strip()
            if not code or not desc:
                continue
            # CPT codes: 5-digit or 4-digit + letter (Category III)
            if not re.match(r"^\d{4,5}[A-Z]?$", code):
                continue
            code_to_desc[code] = desc
            count += 1

            for w in set(re.findall(r"[a-z]{3,}", desc.lower())):
                word_index.setdefault(w, []).append(code)

    logger.info("Loaded %d CPT codes", count)
    return code_to_desc, word_index


# ── Public helpers ─────────────────────────────────────────────────


def is_valid_code(code: str) -> bool:
    """Return ``True`` if the CPT code exists in the official file.

    If the file has not been loaded, returns ``True`` optimistically.
    """
    codes, _ = _load_cpt_data()
    if not codes:
        return True
    return code.strip() in codes


def search_by_name(procedure_name: str, max_results: int = 5) -> list[tuple[str, str]]:
    """Return up to *max_results* ``(code, description)`` pairs whose
    descriptions best match *procedure_name*.
    """
    codes, word_index = _load_cpt_data()
    if not codes:
        return []

    query_words = set(re.findall(r"[a-z]{3,}", procedure_name.lower()))
    if not query_words:
        return []

    scores: dict[str, int] = {}
    for w in query_words:
        for c in word_index.get(w, []):
            scores[c] = scores.get(c, 0) + 1

    if not scores:
        return []

    threshold = max(1, len(query_words) // 2)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(c, codes[c]) for c, s in ranked[:max_results] if s >= threshold]
