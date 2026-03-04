"""scispaCy-based medical Named Entity Recognition agent.

Uses **two specialised scispaCy models** for high-precision extraction:

* ``en_ner_bc5cdr_md``   — trained on BC5CDR corpus → entity labels
  ``CHEMICAL`` (medications / drugs) and ``DISEASE``.
* ``en_ner_bionlp13cg_md`` — trained on BioNLP-13-CG corpus → broader
  biomedical entity labels that cover anatomical structures, cellular
  components, gene products, and procedural language.

A fallback to ``en_core_sci_sm`` (general model, every entity labelled
``ENTITY``) is used when either specialised model is unavailable.

The agent returns:

* ``classified_entities`` — medications / diseases / procedure *candidate*
  names already separated by model label.
* ``raw_entity_names`` — the full deduplicated entity name list (kept for
  backwards compatibility and for the LLM to cross-check).

The downstream LLM enrichment step receives the pre-classified lists so
it can enrich them with contextual details (dosage, severity, etc.) and
catch any entities the NER models missed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import spacy
from spacy.language import Language
from pydantic import BaseModel

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.agents.common.contracts import (
    IAgentInput,
    IAgentOutput,
)

import coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)

AGENT = "scispacy_ner_agent"


# ── I/O schemas ────────────────────────────────────────────────────


class ClassifiedEntity(BaseModel):
    """A single NER-detected entity with provenance metadata."""

    name: str
    source_model: str = ""  # "bc5cdr", "bionlp", "general"
    source_label: str = ""  # e.g. "CHEMICAL", "DISEASE", "ORGAN"
    ner_confidence: float = 0.0  # 0.0–1.0


class ClassifiedEntities(BaseModel):
    """Pre-classified entity names from the NER models."""

    medications: list[ClassifiedEntity] = []
    diseases: list[ClassifiedEntity] = []
    procedure_candidates: list[ClassifiedEntity] = []

    # Convenience: flat name lists for backward-compatible consumers
    def medication_names(self) -> list[str]:
        return [e.name for e in self.medications]

    def disease_names(self) -> list[str]:
        return [e.name for e in self.diseases]

    def procedure_candidate_names(self) -> list[str]:
        return [e.name for e in self.procedure_candidates]


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    classified_entities: ClassifiedEntities = ClassifiedEntities()
    raw_entity_names: list[str] = []


class IScispaCyNERAgentInput(IAgentInput):
    input: IInputData


class IScispaCyNERAgentOutput(IAgentOutput):
    output: IOutputData | None = None


# ── Entity-label → category mapping ───────────────────────────────

# BC5CDR labels
_BC5CDR_MEDICATIONS = frozenset({"CHEMICAL"})
_BC5CDR_DISEASES = frozenset({"DISEASE"})

# BioNLP-13-CG labels that hint at procedures / anatomy.
# We exclude labels that produce mostly noise:
#   ORGANISM        → "Patient", "human" — not procedure-related
#   SIMPLE_CHEMICAL → overlaps with BC5CDR's CHEMICAL
#   CANCER          → a disease, should be caught by BC5CDR DISEASE
#   AMINO_ACID      → biochemistry, not procedures
#   GENE_OR_GENE_PRODUCT → genetics, not procedures
#   CELL / CELLULAR_COMPONENT → too granular
_BIONLP_PROCEDURE_HINTS = frozenset(
    {
        "ORGAN",
        "TISSUE",
        "ANATOMICAL_SYSTEM",
        "DEVELOPING_ANATOMICAL_STRUCTURE",
        "ORGANISM_SUBDIVISION",
        "MULTI-TISSUE_STRUCTURE",
        "PATHOLOGICAL_FORMATION",
        "ORGANISM_SUBSTANCE",
        "IMMATERIAL_ANATOMICAL_ENTITY",
    }
)

# ── Therapeutic drug-class lexicon ─────────────────────────────────
# These high-level class names are clinically important but NER models
# trained for specific drugs/diseases often miss them.  We do a simple
# case-insensitive substring scan of the document text and promote any
# matches into the medication list as DRUG_CLASS entities.
_DRUG_CLASS_LEXICON: list[str] = [
    # Sorted longest-first so substring matching is unambiguous
    "angiotensin receptor blockers",
    "calcium channel blockers",
    "proton pump inhibitors",
    "antiplatelet agents",
    "immunosuppressants",
    "antihypertensives",
    "muscle relaxants",
    "antidepressants",
    "antiepileptics",
    "anticoagulants",
    "antidiabetics",
    "antihistamines",
    "antipsychotics",
    "bronchodilators",
    "corticosteroids",
    "antipyretics",
    "antiemetics",
    "beta blockers",
    "beta-blockers",
    "ace inhibitors",
    "analgesics",
    "antibiotics",
    "antifungals",
    "antivirals",
    "diuretics",
    "hypnotics",
    "laxatives",
    "sedatives",
    "statins",
    "opioids",
    "nsaids",
    "nsaid",
]


# ── Model loading (cached singletons) ─────────────────────────────


@dataclass
class _NERModels:
    """Container for loaded NER models."""

    # Primary: medication + disease extraction
    bc5cdr: Language | None = None
    # Secondary: broader biomedical entity detection
    bionlp: Language | None = None
    # Fallback: general biomedical NER (labels everything "ENTITY")
    general: Language | None = None


@lru_cache(maxsize=1)
def _load_models() -> _NERModels:
    """Load the NER model(s).  Failures are logged but non-fatal."""

    models = _NERModels()

    # ── BC5CDR (chemicals + diseases) ──────────────────────────
    bc5cdr_name = settings.ner_bc5cdr_model
    try:
        models.bc5cdr = spacy.load(bc5cdr_name)
        logger.info(
            "Loaded BC5CDR model '%s' — pipes: %s",
            bc5cdr_name,
            models.bc5cdr.pipe_names,
        )
    except OSError:
        logger.warning(
            "BC5CDR model '%s' not found — medication/disease NER unavailable. "
            "Install with: uv pip install --no-deps "
            "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/"
            "v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz",
            bc5cdr_name,
        )

    # ── BioNLP-13-CG (broader biomedical) ──────────────────────
    bionlp_name = settings.ner_bionlp_model
    try:
        models.bionlp = spacy.load(bionlp_name)
        logger.info(
            "Loaded BioNLP model '%s' — pipes: %s",
            bionlp_name,
            models.bionlp.pipe_names,
        )
    except OSError:
        logger.warning(
            "BioNLP model '%s' not found — procedure NER unavailable. "
            "Install with: uv pip install --no-deps "
            "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/"
            "v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz",
            bionlp_name,
        )

    # ── General fallback ───────────────────────────────────────
    if models.bc5cdr is None and models.bionlp is None:
        general_name = settings.scispacy_model
        try:
            models.general = spacy.load(general_name)
            logger.info(
                "Loaded general model '%s' (fallback) — pipes: %s",
                general_name,
                models.general.pipe_names,
            )
        except OSError:
            logger.error(
                "No NER model available at all.  Install at least en_core_sci_sm: "
                "uv pip install --no-deps "
                "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/"
                "v0.5.4/en_core_sci_sm-0.5.4.tar.gz"
            )

    return models


# ── Helpers ────────────────────────────────────────────────────────


def _dedupe_add(
    name: str,
    target: list[ClassifiedEntity],
    seen: set[str],
    source_model: str = "",
    source_label: str = "",
    ner_confidence: float = 0.0,
) -> None:
    """Append *name* to *target* if not already seen (case-insensitive)."""
    key = name.lower()
    if key not in seen:
        seen.add(key)
        target.append(
            ClassifiedEntity(
                name=name,
                source_model=source_model,
                source_label=source_label,
                ner_confidence=ner_confidence,
            )
        )


def _is_substring_of_seen(name: str, seen: set[str]) -> bool:
    """Return True if *name* is a substring of any entry in *seen*."""
    key = name.lower()
    return any(key in s and key != s for s in seen)


def _dedupe_add_raw(name: str, target: list[str], seen: set[str]) -> None:
    """Simple string dedup for raw_names list."""
    key = name.lower()
    if key not in seen:
        seen.add(key)
        target.append(name)


# ── Main agent function ───────────────────────────────────────────


def run_scispacy_ner_agent(
    payload: IScispaCyNERAgentInput,
) -> IScispaCyNERAgentOutput:
    """Run specialised NER models and return pre-classified entity names.

    Entity classification strategy:

    1. ``en_ner_bc5cdr_md``  →  ``CHEMICAL`` → medications,
                                 ``DISEASE``  → diseases.
    2. ``en_ner_bionlp13cg_md`` →  procedure-related labels
       (ORGAN, TISSUE, ANATOMICAL_SYSTEM, …) are collected as
       **procedure candidates** for the LLM to confirm/reject.
    3. If neither model is available, ``en_core_sci_sm`` supplies
       unclassified ``ENTITY`` spans (same as the old behaviour).
    """
    text = payload.input.text
    logger.info("Running scispaCy NER on text of length %d", len(text))

    try:
        models = _load_models()
    except Exception as e:
        logger.error("Failed to load NER models: %s", e)
        return IScispaCyNERAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="model_load_error",
            output=None,
        )

    medications: list[ClassifiedEntity] = []
    diseases: list[ClassifiedEntity] = []
    procedure_candidates: list[ClassifiedEntity] = []
    raw_names: list[str] = []
    seen_global: set[str] = set()  # dedup across all models
    seen_meds: set[str] = set()
    seen_dis: set[str] = set()
    seen_proc: set[str] = set()

    try:
        # ── BC5CDR pass ────────────────────────────────────────
        if models.bc5cdr is not None:
            doc = models.bc5cdr(text)
            for ent in doc.ents:
                name = ent.text.strip()
                if not name or len(name) < 2:
                    continue

                if ent.label_ in _BC5CDR_MEDICATIONS:
                    _dedupe_add(
                        name,
                        medications,
                        seen_meds,
                        source_model="bc5cdr",
                        source_label=ent.label_,
                        ner_confidence=1.0,  # bc5cdr labels are binary
                    )
                elif ent.label_ in _BC5CDR_DISEASES:
                    _dedupe_add(
                        name,
                        diseases,
                        seen_dis,
                        source_model="bc5cdr",
                        source_label=ent.label_,
                        ner_confidence=1.0,
                    )

                _dedupe_add_raw(name, raw_names, seen_global)

            logger.info(
                "BC5CDR NER: %d medications, %d diseases",
                len(medications),
                len(diseases),
            )

        # ── BioNLP pass ────────────────────────────────────────
        if models.bionlp is not None:
            doc = models.bionlp(text)
            for ent in doc.ents:
                name = ent.text.strip()
                if not name or len(name) < 2:
                    continue

                # Only promote entities to procedure_candidates if
                # they were NOT already classified by BC5CDR as a
                # medication or disease, and are not a substring of
                # an already-classified entity (avoids partial
                # overlaps like "Mellitus" when "Type 2 Diabetes
                # Mellitus" was already tagged).
                key = name.lower()
                if key not in seen_meds and key not in seen_dis:
                    if not _is_substring_of_seen(name, seen_meds | seen_dis):
                        if ent.label_ in _BIONLP_PROCEDURE_HINTS:
                            _dedupe_add(
                                name,
                                procedure_candidates,
                                seen_proc,
                                source_model="bionlp",
                                source_label=ent.label_,
                                ner_confidence=0.7,  # procedure candidates are lower confidence
                            )

                _dedupe_add_raw(name, raw_names, seen_global)

            logger.info(
                "BioNLP NER: %d procedure candidates (new entities from this pass)",
                len(procedure_candidates),
            )

        # ── Drug-class lexicon scan ────────────────────────────
        text_lower = text.lower()
        for class_term in _DRUG_CLASS_LEXICON:
            if class_term in text_lower:
                canonical = class_term.title()
                _dedupe_add(
                    canonical,
                    medications,
                    seen_meds,
                    source_model="class_lexicon",
                    source_label="DRUG_CLASS",
                    ner_confidence=0.5,
                )
                _dedupe_add_raw(canonical, raw_names, seen_global)

        if medications:
            logger.info(
                "Drug-class lexicon: total %d medications after class scan",
                len(medications),
            )

        # ── General fallback ───────────────────────────────────
        if (
            models.bc5cdr is None
            and models.bionlp is None
            and models.general is not None
        ):
            doc = models.general(text)
            for ent in doc.ents:
                name = ent.text.strip()
                if not name or len(name) < 2:
                    continue
                _dedupe_add_raw(name, raw_names, seen_global)

            logger.info(
                "General fallback NER: %d unclassified entities",
                len(raw_names),
            )

    except Exception as e:
        logger.error("scispaCy NER failed: %s", e)
        return IScispaCyNERAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    logger.info(
        "NER totals — %d medications, %d diseases, %d procedure candidates, "
        "%d raw entity names",
        len(medications),
        len(diseases),
        len(procedure_candidates),
        len(raw_names),
    )

    return IScispaCyNERAgentOutput(
        rund_id=payload.rund_id,
        status="completed",
        output=IOutputData(
            classified_entities=ClassifiedEntities(
                medications=medications,
                diseases=diseases,
                procedure_candidates=procedure_candidates,
            ),
            raw_entity_names=raw_names,
        ),
    )
