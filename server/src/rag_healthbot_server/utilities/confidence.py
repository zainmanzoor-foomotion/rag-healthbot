"""
Confidence scoring framework for the multi-layer code resolution pipeline.

Each resolution signal contributes a weighted score.  The final confidence
is a weighted average in [0, 1].  An entity is auto-accepted when
confidence >= settings.auto_accept_threshold (default 0.85).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from rag_healthbot_server.config import settings

logger = logging.getLogger(__name__)

# ── Signal weights (must sum to 1.0) ─────────────────────────────────

SIGNAL_WEIGHTS: dict[str, float] = {
    "ner_score": 0.10,
    "llm_score": 0.10,
    "umls_match_score": 0.25,
    "code_validation_score": 0.25,
    "kb_semantic_score": 0.20,
    "synonym_boost": 0.10,
}

assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1"


# ── Dataclasses ───────────────────────────────────────────────────────


@dataclass
class CandidateCode:
    """A single candidate produced by one resolution layer."""

    code: str
    cui: str | None = None
    description: str = ""
    source: str = ""  # e.g. "umls_exact", "kb_semantic", "local_search"
    raw_score: float = 0.0


@dataclass
class ResolutionSignals:
    """Scores from individual pipeline layers (each in 0‥1)."""

    ner_score: float = 0.0
    llm_score: float = 0.0
    umls_match_score: float = 0.0
    code_validation_score: float = 0.0
    kb_semantic_score: float = 0.0
    synonym_boost: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "ner_score": self.ner_score,
            "llm_score": self.llm_score,
            "umls_match_score": self.umls_match_score,
            "code_validation_score": self.code_validation_score,
            "kb_semantic_score": self.kb_semantic_score,
            "synonym_boost": self.synonym_boost,
        }


@dataclass
class CodeResolution:
    """Final, immutable result of multi-layer resolution for one entity."""

    cui: str | None = None
    code: str | None = None  # ICD-10-CM / CPT / RxNorm
    confidence: float = 0.0
    review_status: str = "pending_review"  # accepted | pending_review | rejected
    resolution_method: str = ""  # which layer produced the winning code
    signals: ResolutionSignals = field(default_factory=ResolutionSignals)
    candidates: list[CandidateCode] = field(default_factory=list)

    def candidates_as_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "code": c.code,
                "cui": c.cui,
                "description": c.description,
                "source": c.source,
                "raw_score": c.raw_score,
            }
            for c in self.candidates
        ]


# ── Scoring helpers ───────────────────────────────────────────────────


def compute_confidence(signals: ResolutionSignals) -> float:
    """Return weighted‐average confidence in [0, 1]."""
    sig = signals.as_dict()
    total = sum(SIGNAL_WEIGHTS[k] * sig[k] for k in SIGNAL_WEIGHTS)
    return round(min(max(total, 0.0), 1.0), 4)


def should_auto_accept(confidence: float) -> bool:
    return confidence >= settings.auto_accept_threshold


def determine_review_status(signals: ResolutionSignals) -> str:
    """
    Hard rules that override confidence:
      • code_validation_score == 0  → always pending_review
      • no CUI found               → handled by caller
    Otherwise fall back to threshold.
    """
    if signals.code_validation_score == 0.0:
        return "pending_review"
    confidence = compute_confidence(signals)
    return "accepted" if should_auto_accept(confidence) else "pending_review"


def build_resolution(
    *,
    cui: str | None,
    code: str | None,
    resolution_method: str,
    signals: ResolutionSignals,
    candidates: list[CandidateCode] | None = None,
) -> CodeResolution:
    """
    Convenience constructor: computes confidence and review_status from signals.
    """
    confidence = compute_confidence(signals)
    review_status = determine_review_status(signals)

    return CodeResolution(
        cui=cui,
        code=code,
        confidence=confidence,
        review_status=review_status,
        resolution_method=resolution_method,
        signals=signals,
        candidates=candidates or [],
    )
