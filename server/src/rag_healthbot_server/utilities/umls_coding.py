"""UMLS coding utility — CUI / ICD-10-CM / CPT resolution.

Multi-layer resolution pipeline
---------------------------------
Each ``resolve_*`` function now returns a :class:`CodeResolution` that
carries confidence, review_status, per-signal scores, and a list of
candidate codes encountered along the way.

Resolution layers (executed in order, first valid code wins):

1. **UMLS exact/words/approximate search** → CUI → code atoms
2. **Local code-file validation** (confirm atom code is in ICD-10/CPT file)
3. **KB semantic search** (embed entity name → cosine search over code descriptions)
4. **Local name search** with synonym expansion (icd10_lookup / cpt_lookup)
5. **UMLS synonym retry** (preferred name + atom synonyms)

All UMLS REST calls are LRU-cached so repeated lookups are almost free.
When no API key is configured the functions gracefully return ``None``.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

import httpx

from rag_healthbot_server.config import settings
from rag_healthbot_server.utilities import cpt_lookup, icd10_lookup
from rag_healthbot_server.utilities.confidence import (
    CandidateCode,
    CodeResolution,
    ResolutionSignals,
    build_resolution,
)

logger = logging.getLogger(__name__)

_UMLS_BASE = "https://uts-ws.nlm.nih.gov/rest"
_TIMEOUT = 15.0  # seconds per request

# ── TUI sets (kept for reference / future classification) ─────────

MEDICATION_TUIS: frozenset[str] = frozenset(
    {"T116", "T121", "T125", "T126", "T129", "T195", "T200", "T109", "T131"}
)
DISEASE_TUIS: frozenset[str] = frozenset(
    {"T019", "T033", "T037", "T046", "T047", "T048", "T184", "T190", "T191"}
)
PROCEDURE_TUIS: frozenset[str] = frozenset(
    {"T058", "T059", "T060", "T061", "T062", "T063"}
)


def classify_tui(tuis: set[str]) -> str | None:
    """Return ``'medication'``, ``'disease'``, or ``'procedure'``."""
    if tuis & MEDICATION_TUIS:
        return "medication"
    if tuis & DISEASE_TUIS:
        return "disease"
    if tuis & PROCEDURE_TUIS:
        return "procedure"
    return None


# ── Internal helpers ──────────────────────────────────────────────


def _has_api_key() -> bool:
    return bool(settings.umls_api_key)


def _normalize_entity_name(name: str) -> str:
    """Strip parenthetical qualifiers, trailing NOS / unspecified, etc."""
    cleaned = re.sub(r"\s*\([^)]*\)", "", name)
    cleaned = re.sub(
        r",?\s*(unspecified|NOS|not otherwise specified)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip()


# ── UMLS REST primitives ─────────────────────────────────────────


@lru_cache(maxsize=2048)
def search_umls(term: str, sab: str | None = None) -> str | None:
    """Search UMLS for *term*; return the best CUI or ``None``.

    Tries exact → words → approximate in order.
    """
    if not _has_api_key() or not term.strip():
        return None

    url = f"{_UMLS_BASE}/search/current"
    params: dict[str, str | int] = {
        "apiKey": settings.umls_api_key,
        "string": term,
        "pageSize": 1,
    }
    if sab:
        params["sabs"] = sab

    for strategy in ("exact", "words", "approximate"):
        try:
            params["searchType"] = strategy
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(url, params=params)
            if resp.status_code in (401, 404):
                continue
            resp.raise_for_status()
            results = resp.json().get("result", {}).get("results", [])
            if results and results[0].get("ui") != "NONE":
                cui = results[0]["ui"]
                logger.debug("UMLS search (%s) '%s' → CUI %s", strategy, term, cui)
                return cui
        except Exception as exc:
            logger.warning("UMLS %s search failed for '%s': %s", strategy, term, exc)
    return None


@lru_cache(maxsize=2048)
def _get_atoms(cui: str, sab: str) -> list[dict]:
    """Fetch atom dicts for *cui* from source vocabulary *sab*."""
    if not _has_api_key():
        return []
    url = f"{_UMLS_BASE}/content/current/CUI/{cui}/atoms"
    params = {"apiKey": settings.umls_api_key, "sabs": sab, "pageSize": 25}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("result", [])
        return []
    except Exception as exc:
        logger.debug("UMLS atoms error CUI=%s SAB=%s: %s", cui, sab, exc)
        return []


def _extract_code(atoms: list[dict]) -> str | None:
    """Pull the first non-empty code from UMLS atom dicts."""
    for atom in atoms:
        raw = atom.get("code", "")
        if "/" in raw:
            raw = raw.rsplit("/", 1)[-1]
        raw = raw.strip()
        if raw and raw != "NOCODE":
            return raw
    return None


@lru_cache(maxsize=2048)
def cui_to_icd10(cui: str) -> str | None:
    """CUI → raw ICD-10-CM code from UMLS atoms (may contain dots)."""
    code = _extract_code(_get_atoms(cui, "ICD10CM"))
    if not code:
        # Fallback: international ICD-10 (not US clinical modification)
        code = _extract_code(_get_atoms(cui, "ICD10"))
    return code


@lru_cache(maxsize=2048)
def cui_to_cpt(cui: str) -> str | None:
    """CUI → CPT code from UMLS atoms."""
    code = _extract_code(_get_atoms(cui, "CPT"))
    if not code:
        code = _extract_code(_get_atoms(cui, "HCPCS"))
    return code


@lru_cache(maxsize=2048)
def cui_to_tuis(cui: str) -> set[str]:
    """Fetch semantic types (TUIs) for a CUI.  Empty set on failure."""
    if not _has_api_key():
        return set()
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_UMLS_BASE}/content/current/CUI/{cui}",
                params={"apiKey": settings.umls_api_key},
            )
        if resp.status_code == 200:
            stys = resp.json().get("result", {}).get("semanticTypes", [])
            return {s.get("uri", "").rsplit("/", 1)[-1] for s in stys} - {""}
    except Exception:
        pass
    return set()


@lru_cache(maxsize=2048)
def _cui_preferred_name(cui: str) -> str | None:
    """Fetch the UMLS preferred name for a CUI."""
    if not _has_api_key():
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_UMLS_BASE}/content/current/CUI/{cui}",
                params={"apiKey": settings.umls_api_key},
            )
        if resp.status_code == 200:
            return resp.json().get("result", {}).get("name")
    except Exception:
        pass
    return None


@lru_cache(maxsize=512)
def _cui_synonyms(cui: str) -> list[str]:
    """Fetch English atom names for a CUI (synonyms / alternative names)."""
    if not _has_api_key():
        return []
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_UMLS_BASE}/content/current/CUI/{cui}/atoms",
                params={
                    "apiKey": settings.umls_api_key,
                    "language": "ENG",
                    "pageSize": 25,
                },
            )
        if resp.status_code == 200:
            atoms = resp.json().get("result", [])
            seen: set[str] = set()
            names: list[str] = []
            for atom in atoms:
                name = atom.get("name", "").strip()
                low = name.lower()
                if name and low not in seen:
                    seen.add(low)
                    names.append(name)
            return names
    except Exception:
        pass
    return []


# ── ICD-10-CM validation / refinement ────────────────────────────


def _validate_and_refine_icd10(raw_code: str) -> str | None:
    """Normalize, validate against local file, refine to specific code."""
    normalized = icd10_lookup.normalize_code(raw_code)

    # Exact match in local file → done
    if icd10_lookup.is_valid_code(normalized):
        return normalized

    # Try to refine (parent code → most specific child)
    refined, desc = icd10_lookup.refine_code(normalized)
    if desc is not None:
        return refined

    # Not in local file — still return normalized (dots stripped)
    logger.warning(
        "ICD-10-CM code '%s' not found in local file (normalized from '%s')",
        normalized,
        raw_code,
    )
    return normalized


# ── CPT validation ───────────────────────────────────────────────


def _validate_cpt(raw_code: str) -> str | None:
    """Return the code if valid, else ``None``."""
    code = raw_code.strip()
    if not code:
        return None
    if cpt_lookup.is_valid_code(code):
        return code
    # If no local file, accept any plausible CPT format
    if re.match(r"^\d{4,5}[A-Z]?$", code):
        return code
    return None


# ── Public resolve functions (multi-layer pipeline) ──────────────


def resolve_disease_codes(
    name: str,
    *,
    ner_score: float = 0.0,
    llm_score: float = 0.0,
) -> CodeResolution:
    """Resolve a disease name to a ``CodeResolution`` with CUI + ICD-10-CM.

    Pipeline layers:
    1. UMLS search → CUI → ICD10CM atoms → validate + refine
    2. KB semantic search over ICD-10 descriptions
    3. Local ICD-10 file name search (synonym expansion)
    4. UMLS synonym retry
    """
    candidates: list[CandidateCode] = []
    cui: str | None = None
    icd10: str | None = None
    resolution_method = ""
    umls_match = 0.0
    code_valid = 0.0
    kb_score = 0.0
    syn_boost = 0.0

    # ── Layer 1: UMLS search ──────────────────────────────────────
    cui, icd10_raw = _resolve_disease_via_umls(name)
    if cui:
        umls_match = 1.0 if icd10_raw else 0.6
    if icd10_raw:
        icd10 = _validate_and_refine_icd10(icd10_raw)
        if icd10 and icd10_lookup.is_valid_code(icd10):
            code_valid = 1.0
            resolution_method = "umls_atoms"
            candidates.append(
                CandidateCode(code=icd10, cui=cui, source="umls_atoms", raw_score=1.0)
            )
        elif icd10:
            code_valid = 0.5  # code present but not in local file
            resolution_method = "umls_atoms_unvalidated"
            candidates.append(
                CandidateCode(
                    code=icd10, cui=cui, source="umls_atoms_unvalidated", raw_score=0.5
                )
            )

    # Retry with normalised name
    if not cui or not icd10:
        normalized = _normalize_entity_name(name)
        if normalized and normalized.lower() != name.lower():
            cui2, icd10_2_raw = _resolve_disease_via_umls(normalized)
            if not cui and cui2:
                cui = cui2
                umls_match = max(umls_match, 0.8)
            if not icd10 and icd10_2_raw:
                icd10 = _validate_and_refine_icd10(icd10_2_raw)
                if icd10 and icd10_lookup.is_valid_code(icd10):
                    code_valid = 1.0
                    resolution_method = resolution_method or "umls_normalized"
                    candidates.append(
                        CandidateCode(
                            code=icd10,
                            cui=cui,
                            source="umls_normalized",
                            raw_score=0.9,
                        )
                    )

    # ── Layer 2: KB semantic search ───────────────────────────────
    if not icd10:
        try:
            from rag_healthbot_server.utilities.kb_search import kb_search

            kb_hits = kb_search(name, "icd10", top_k=3)
            for hit in kb_hits:
                candidates.append(
                    CandidateCode(
                        code=hit.code,
                        description=hit.description,
                        source="kb_semantic",
                        raw_score=hit.similarity,
                    )
                )
            if kb_hits and kb_hits[0].similarity >= 0.75:
                icd10 = kb_hits[0].code
                kb_score = kb_hits[0].similarity
                code_valid = 1.0 if icd10_lookup.is_valid_code(icd10) else 0.5
                resolution_method = resolution_method or "kb_semantic"
        except Exception:
            logger.debug("KB search skipped (not indexed yet?)")

    # ── Layer 3: local name search with synonym expansion ─────────
    if not icd10:
        search_terms = [name]
        if cui:
            pref = _cui_preferred_name(cui)
            if pref and pref.lower() != name.lower():
                search_terms.append(pref)
            for syn in _cui_synonyms(cui):
                if syn.lower() not in {t.lower() for t in search_terms}:
                    search_terms.append(syn)
                if len(search_terms) >= 8:
                    break
            syn_boost = 0.5  # used synonyms

        best_score = -1.0
        for term in search_terms:
            local = icd10_lookup.search_by_name(term, max_results=1, return_scores=True)
            if local:
                code, desc, score = local[0]
                candidates.append(
                    CandidateCode(
                        code=code,
                        description=desc,
                        source="local_name_search",
                        raw_score=score,
                    )
                )
                if score > best_score:
                    best_score = score
                    icd10 = code
        if icd10:
            code_valid = 1.0
            resolution_method = resolution_method or "local_name_search"
            # Normalize score — local scores are raw BM25-like numbers
            syn_boost = min(1.0, syn_boost + (0.3 if best_score > 10 else 0.0))

    # ── Build final resolution ────────────────────────────────────
    signals = ResolutionSignals(
        ner_score=min(ner_score, 1.0),
        llm_score=min(llm_score, 1.0),
        umls_match_score=umls_match,
        code_validation_score=code_valid,
        kb_semantic_score=kb_score,
        synonym_boost=syn_boost,
    )

    return build_resolution(
        cui=cui,
        code=icd10,
        resolution_method=resolution_method,
        signals=signals,
        candidates=candidates,
    )


def _resolve_disease_via_umls(name: str) -> tuple[str | None, str | None]:
    """Try UMLS general search → CUI → ICD10CM atoms."""
    cui = search_umls(name)
    icd10: str | None = None

    if cui:
        raw = cui_to_icd10(cui)
        if raw:
            icd10 = _validate_and_refine_icd10(raw)

    return cui, icd10


def resolve_procedure_codes(
    name: str,
    *,
    ner_score: float = 0.0,
    llm_score: float = 0.0,
) -> CodeResolution:
    """Resolve a procedure name to a ``CodeResolution`` with CUI + CPT.

    Pipeline layers:
    1. UMLS search → CUI → CPT/HCPCS atoms → validate
    2. KB semantic search over CPT descriptions
    3. Local CPT file name search
    4. UMLS synonym retry
    """
    candidates: list[CandidateCode] = []
    cui: str | None = None
    cpt: str | None = None
    resolution_method = ""
    umls_match = 0.0
    code_valid = 0.0
    kb_score = 0.0
    syn_boost = 0.0

    # ── Layer 1: UMLS search ──────────────────────────────────────
    cui, cpt_raw = _resolve_procedure_via_umls(name)
    if cui:
        umls_match = 1.0 if cpt_raw else 0.6
    if cpt_raw:
        cpt = _validate_cpt(cpt_raw)
        if cpt:
            code_valid = 1.0
            resolution_method = "umls_atoms"
            candidates.append(
                CandidateCode(code=cpt, cui=cui, source="umls_atoms", raw_score=1.0)
            )
        else:
            candidates.append(
                CandidateCode(
                    code=cpt_raw, cui=cui, source="umls_atoms_invalid", raw_score=0.3
                )
            )

    # Retry with normalized name
    if not cui or not cpt:
        normalized = _normalize_entity_name(name)
        if normalized and normalized.lower() != name.lower():
            cui2, cpt2_raw = _resolve_procedure_via_umls(normalized)
            if not cui and cui2:
                cui = cui2
                umls_match = max(umls_match, 0.8)
            if not cpt and cpt2_raw:
                cpt = _validate_cpt(cpt2_raw)
                if cpt:
                    code_valid = 1.0
                    resolution_method = resolution_method or "umls_normalized"
                    candidates.append(
                        CandidateCode(
                            code=cpt,
                            cui=cui,
                            source="umls_normalized",
                            raw_score=0.9,
                        )
                    )

    # ── Layer 2: KB semantic search ───────────────────────────────
    if not cpt:
        try:
            from rag_healthbot_server.utilities.kb_search import kb_search

            kb_hits = kb_search(name, "cpt", top_k=3)
            for hit in kb_hits:
                candidates.append(
                    CandidateCode(
                        code=hit.code,
                        description=hit.description,
                        source="kb_semantic",
                        raw_score=hit.similarity,
                    )
                )
            if kb_hits and kb_hits[0].similarity >= 0.75:
                cpt = kb_hits[0].code
                kb_score = kb_hits[0].similarity
                code_valid = 1.0 if cpt_lookup.is_valid_code(cpt) else 0.5
                resolution_method = resolution_method or "kb_semantic"
        except Exception:
            logger.debug("KB search skipped (not indexed yet?)")

    # ── Layer 3: local CPT name search ────────────────────────────
    if not cpt:
        local = cpt_lookup.search_by_name(name, max_results=1)
        if local:
            cpt = local[0][0]
            code_valid = 1.0
            resolution_method = resolution_method or "local_name_search"
            candidates.append(
                CandidateCode(
                    code=cpt,
                    description=local[0][1],
                    source="local_name_search",
                    raw_score=0.7,
                )
            )

    # ── Build final resolution ────────────────────────────────────
    signals = ResolutionSignals(
        ner_score=min(ner_score, 1.0),
        llm_score=min(llm_score, 1.0),
        umls_match_score=umls_match,
        code_validation_score=code_valid,
        kb_semantic_score=kb_score,
        synonym_boost=syn_boost,
    )

    return build_resolution(
        cui=cui,
        code=cpt,
        resolution_method=resolution_method,
        signals=signals,
        candidates=candidates,
    )


def _resolve_procedure_via_umls(name: str) -> tuple[str | None, str | None]:
    """Try UMLS general search → CUI → CPT / HCPCS atoms."""
    cui = search_umls(name)
    cpt: str | None = None

    if cui:
        raw = cui_to_cpt(cui)
        if raw:
            cpt = _validate_cpt(raw)

    return cui, cpt


def resolve_medication_cui(
    name: str,
    *,
    ner_score: float = 0.0,
    llm_score: float = 0.0,
) -> CodeResolution:
    """Look up the UMLS CUI for a medication name.

    Returns a ``CodeResolution`` (code field is left ``None`` —
    RxNorm/NDC is resolved elsewhere).
    """
    cui = search_umls(name)
    umls_match = 1.0 if cui else 0.0

    if not cui:
        normalized = _normalize_entity_name(name)
        if normalized and normalized.lower() != name.lower():
            cui = search_umls(normalized)
            if cui:
                umls_match = 0.8

    signals = ResolutionSignals(
        ner_score=min(ner_score, 1.0),
        llm_score=min(llm_score, 1.0),
        umls_match_score=umls_match,
        # No code to validate for medications (CUI-only)
        code_validation_score=1.0 if cui else 0.0,
        kb_semantic_score=0.0,
        synonym_boost=0.0,
    )

    return build_resolution(
        cui=cui,
        code=None,
        resolution_method="umls_search" if cui else "",
        signals=signals,
    )
