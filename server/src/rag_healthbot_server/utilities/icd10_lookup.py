"""Local ICD-10-CM code validation and refinement.

Loads the official ICD-10-CM code file and provides:

* **Validation** – is a code real / billable?
* **Refinement** – given a truncated parent code, find the most specific child
* **Name search** – find codes by disease description (word-overlap scoring)

The file format is one code per line::

    A000    Cholera due to Vibrio cholerae 01, biovar cholerae
    K631    Perforation of intestine (nontraumatic)
    ...

Call :func:`set_icd10_file` at application startup to point this module at
the correct file path.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_ICD10_FILE: Path | None = None


# ── Startup configuration ─────────────────────────────────────────


def set_icd10_file(path: str | Path) -> None:
    """Set the path to the ICD-10-CM code file.  Clears the cache."""
    global _ICD10_FILE
    _ICD10_FILE = Path(path)
    _load_icd10_data.cache_clear()
    logger.info("ICD-10-CM file set to: %s", _ICD10_FILE)


# ── Data loading (cached) ─────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_icd10_data() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return ``(code_to_desc, word_index)``.

    * ``code_to_desc`` maps e.g. ``"K631"`` → ``"Perforation of intestine …"``
    * ``word_index`` maps each lowercase word (≥3 chars) to the list of codes
      whose description contains it.
    """
    code_to_desc: dict[str, str] = {}
    word_index: dict[str, list[str]] = {}

    if _ICD10_FILE is None or not _ICD10_FILE.exists():
        logger.warning("ICD-10-CM file not configured or missing: %s", _ICD10_FILE)
        return code_to_desc, word_index

    logger.info("Loading ICD-10-CM codes from %s …", _ICD10_FILE)
    count = 0

    with open(_ICD10_FILE, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # Format: CODE<whitespace>DESCRIPTION
            m = re.match(r"^([A-Z0-9]{3,7})\s+(.+)$", line)
            if not m:
                continue
            code, desc = m.group(1).upper(), m.group(2).strip()
            code_to_desc[code] = desc
            count += 1

            for w in set(re.findall(r"[a-z]{3,}", desc.lower())):
                word_index.setdefault(w, []).append(code)

    logger.info("Loaded %d ICD-10-CM codes", count)
    return code_to_desc, word_index


# ── Public helpers ─────────────────────────────────────────────────


def normalize_code(code: str) -> str:
    """Remove dots and uppercase: ``'T85.59'`` → ``'T8559'``."""
    return code.upper().replace(".", "").strip()


def is_valid_code(code: str) -> bool:
    """Return ``True`` if the code exists in the official file.

    If the file has not been loaded, returns ``True`` optimistically.
    """
    codes, _ = _load_icd10_data()
    if not codes:
        return True  # can't validate → accept
    return normalize_code(code) in codes


def refine_code(code: str) -> tuple[str, str | None]:
    """Given a (possibly truncated) ICD-10-CM code, return the best
    specific child code.

    Returns ``(best_code, description)`` or ``(original, None)`` when no
    refinement is possible.

    Strategy when the exact code is **not** in the file:

    1. Collect all child codes that start with the same prefix.
    2. Prefer *"unspecified"* descriptions.
    3. Prefer *initial encounter* (suffix ``A``) over subsequent / sequela.
    4. Shortest code first (more general).
    """
    codes, _ = _load_icd10_data()
    if not codes:
        return code, None

    norm = normalize_code(code)

    # Already valid
    if norm in codes:
        return norm, codes[norm]

    # Collect children
    children = [
        (c, d) for c, d in codes.items() if c.startswith(norm) and len(c) > len(norm)
    ]
    if not children:
        logger.debug("No ICD-10-CM children found for '%s'", norm)
        return norm, None

    def _rank(item: tuple[str, str]) -> tuple[int, int, int, str]:
        c, d = item
        dl = d.lower()
        unspec = 0 if "unspecified" in dl else 1
        if "initial encounter" in dl or c.endswith("A"):
            enc = 0
        elif "subsequent" in dl or c.endswith("D"):
            enc = 1
        elif "sequela" in dl or c.endswith("S"):
            enc = 2
        else:
            enc = 0
        return (unspec, enc, len(c), c)

    children.sort(key=_rank)
    best, desc = children[0]
    logger.info(
        "Refined ICD-10-CM '%s' → '%s' (%s) [%d candidates]",
        norm,
        best,
        desc,
        len(children),
    )
    return best, desc


# ── Medical synonym equivalence classes ────────────────────────────
# Each set groups words that refer to the same body system / concept.
# When a query contains one of these words, codes whose descriptions
# contain *any* synonym in the same class get credit for that "slot".

_SYNONYM_CLASSES: list[set[str]] = [
    {
        "gastrointestinal",
        "intestinal",
        "intestine",
        "bowel",
        "enteric",
        "digestive",
        "colonic",
        "colon",
        "rectal",
        "rectum",
        "gastric",
        "stomach",
        "duodenal",
        "duodenum",
        "jejunal",
        "ileal",
    },
    {"cardiac", "heart", "coronary", "myocardial", "cardiovascular"},
    {"pulmonary", "lung", "respiratory", "bronchial", "bronchus"},
    {"renal", "kidney", "nephric", "nephrotic"},
    {"hepatic", "liver", "hepato", "hepatobiliary"},
    {"cerebral", "brain", "intracranial", "cerebro"},
    {"ocular", "eye", "ophthalmic", "optic"},
    {"cutaneous", "skin", "dermal", "dermatologic", "epidermal"},
    {"vascular", "vessel", "arterial", "venous"},
    {"osseous", "bone", "skeletal", "bony"},
    {"muscular", "muscle", "myopathy", "myalgia"},
    {"urinary", "bladder", "vesical", "ureteral", "ureter"},
    {"pancreatic", "pancreas"},
    {"thyroid", "thyroidal"},
    {"adrenal", "suprarenal"},
    {"spleen", "splenic"},
]

_MEDICAL_EXPANSIONS: dict[str, set[str]] = {}
for _cls in _SYNONYM_CLASSES:
    for _word in _cls:
        _MEDICAL_EXPANSIONS[_word] = _cls - {_word}


def search_by_name(
    disease_name: str,
    max_results: int = 5,
    return_scores: bool = False,
) -> list[tuple[str, str]] | list[tuple[str, str, float]]:
    """Return up to *max_results* ``(code, description)`` pairs whose
    descriptions best match *disease_name*.

    If *return_scores* is ``True``, each tuple includes a trailing float
    representing the IDF-weighted match score (higher = better).

    Uses IDF-weighted scoring with **medical synonym expansion**: each
    query word is expanded into an equivalence group (e.g.
    "gastrointestinal" also matches "intestine", "bowel", etc.).  A code
    earns credit for a word-group if *any* word in the group appears in
    its description, ensuring vocabulary gaps between UMLS concept names
    and ICD-10 descriptions are bridged.
    """
    codes, word_index = _load_icd10_data()
    if not codes:
        return []

    query_words = set(re.findall(r"[a-z]{3,}", disease_name.lower()))
    if not query_words:
        return []

    # Stopwords that appear in very many descriptions — skip to reduce noise
    _STOP = {
        "the",
        "and",
        "with",
        "for",
        "not",
        "other",
        "due",
        "type",
        "without",
        "nos",
        "disorder",
    }
    query_words -= _STOP

    if not query_words:
        return []

    import math

    total_codes = len(codes) or 1

    # Build word groups: each original query word + its medical synonyms.
    # This lets "gastrointestinal perforation" match "Perforation of
    # intestine" because "intestine" is a synonym of "gastrointestinal".
    word_groups: list[set[str]] = []
    for w in query_words:
        group = {w}
        expansions = _MEDICAL_EXPANSIONS.get(w)
        if expansions:
            group |= expansions
        word_groups.append(group)

    scores: dict[str, float] = {}
    group_hits: dict[str, int] = {}  # how many word-groups matched per code

    for group in word_groups:
        # Collect the UNION of all codes matching ANY word in this group.
        # Compute a single group-level IDF so that word-form variations
        # (e.g. "intestinal" vs "intestine") contribute equally.
        group_codes: set[str] = set()
        for w in group:
            matching = word_index.get(w, [])
            group_codes.update(matching)

        if not group_codes:
            continue

        group_idf = math.log2(total_codes / (1 + len(group_codes)))

        for c in group_codes:
            scores[c] = scores.get(c, 0.0) + group_idf
            group_hits[c] = group_hits.get(c, 0) + 1

    if not scores:
        return []

    # Must match at least half the word-groups
    threshold = max(1, len(word_groups) // 2)

    # Coverage ratio = group_hits / description content words.
    # Descriptions that are "mostly about" the query rank higher.
    # This prevents overly-specific codes (with many extra words like
    # "Acute duodenal ulcer with perforation") from outranking the
    # generic match ("Perforation of intestine").
    def _coverage(code: str) -> float:
        desc_words = set(re.findall(r"[a-z]{3,}", codes[code].lower())) - _STOP
        return group_hits.get(code, 0) / max(1, len(desc_words))

    ranked = sorted(
        scores.items(),
        key=lambda kv: (
            -group_hits.get(kv[0], 0),  # primary: more groups matched
            -_coverage(kv[0]),  # secondary: higher coverage
            -kv[1],  # tertiary: higher IDF score
            len(kv[0]),  # shorter code (more general)
            kv[0],  # alphabetical
        ),
    )
    results = [
        (c, codes[c], s) if return_scores else (c, codes[c])
        for c, s in ranked[:max_results]
        if group_hits.get(c, 0) >= threshold
    ]
    return results
