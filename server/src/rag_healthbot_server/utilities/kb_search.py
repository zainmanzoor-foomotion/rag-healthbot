"""
Knowledge-base semantic search over ICD-10-CM / CPT code descriptions.

Uses pre-indexed embeddings in the code_embedding table and an Ollama
embedder to turn an entity name into a query vector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_ollama import OllamaEmbeddings

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.db.CodeEmbeddingRepo import search_code_embeddings

logger = logging.getLogger(__name__)

# ── Module-level singleton ────────────────────────────────────────────

_embedder: OllamaEmbeddings | None = None


def _get_embedder() -> OllamaEmbeddings:
    global _embedder
    if _embedder is None:
        if not settings.ollama_host or not settings.ollama_embed_model:
            raise ValueError("OLLAMA_HOST and OLLAMA_MODEL must be set")
        _embedder = OllamaEmbeddings(
            base_url=settings.ollama_host, model=settings.ollama_embed_model
        )
    return _embedder


# ── Public API ────────────────────────────────────────────────────────


@dataclass
class KBMatch:
    code: str
    description: str
    similarity: float  # 1 - cosine_distance, in [0, 1]


def kb_search(
    entity_name: str,
    code_system: str,  # "icd10" | "cpt"
    top_k: int = 5,
) -> list[KBMatch]:
    """
    Embed *entity_name* and find the closest code descriptions in the KB.
    Returns up to *top_k* matches sorted by descending similarity.
    """
    if not entity_name or not entity_name.strip():
        return []

    try:
        embedder = _get_embedder()
        query_vec = embedder.embed_query(entity_name.strip())
    except Exception:
        logger.exception("Failed to embed query '%s'", entity_name)
        return []

    try:
        hits = search_code_embeddings(query_vec, code_system, top_k=top_k)
    except Exception:
        logger.exception("KB search failed for '%s' (%s)", entity_name, code_system)
        return []

    results: list[KBMatch] = []
    for emb, dist in hits:
        similarity = max(0.0, 1.0 - dist)
        results.append(
            KBMatch(code=emb.code, description=emb.description, similarity=similarity)
        )
    return results
