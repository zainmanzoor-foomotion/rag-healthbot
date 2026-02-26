from __future__ import annotations

from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel
import logging
import coloredlogs

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.db.ReportEmbeddingRepo import (
    create_report_embeddings,
    delete_report_embeddings_by_report_id,
    IReportEmbeddings,
)

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "embeddings_agent"


class IInputData(BaseModel):
    texts: list[str]


class IOutputData(BaseModel):
    report_id: int
    chunk_count: int
    embedding_dim: int


class IEmbeddingsAgentInput(IAgentInput):
    input: IInputData


class IEmbeddingsAgentOutput(IAgentOutput):
    output: IOutputData | None = None


def _make_embedder() -> OllamaEmbeddings:
    if not settings.ollama_host or not settings.ollama_embed_model:
        raise ValueError("OLLAMA_HOST and OLLAMA_MODEL must be set")
    return OllamaEmbeddings(
        base_url=settings.ollama_host, model=settings.ollama_embed_model
    )


def _chunk_texts(texts: list[str]) -> list[str]:
    joined = "\n\n".join(t for t in texts if t and t.strip())
    if not joined.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(joined)
    return [c.strip() for c in chunks if c and c.strip()]


def _get_report_id(payload: IEmbeddingsAgentInput) -> int:
    constraints = payload.constraints or {}
    report_id = constraints.get("report_id")
    if report_id is None:
        raise ValueError("Missing constraints.report_id")
    return int(report_id)


def run_embeddings_agent(payload: IEmbeddingsAgentInput) -> IEmbeddingsAgentOutput:
    logger.info(
        "Running embeddings agent for rund_id=%s with %d input texts",
        payload.rund_id,
        len(payload.input.texts or []),
    )

    try:
        report_id = _get_report_id(payload)
    except Exception as e:
        logger.error("Invalid embeddings payload: %s", e)
        return IEmbeddingsAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="invalid_input",
            output=None,
        )

    try:
        chunks = _chunk_texts(payload.input.texts)
        if not chunks:
            raise ValueError("No text available for embeddings")

        embedder = _make_embedder()
        logger.info(
            "Generating embeddings for report_id=%s with %d chunks",
            report_id,
            len(chunks),
        )
        vectors = embedder.embed_documents(chunks)

        if not vectors:
            raise RuntimeError("Embedding model returned no vectors")

        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(vectors)} vectors for {len(chunks)} chunks"
            )

        embedding_dim = len(vectors[0])
        expected_dim = int(settings.vector_dimension or 0)
        if expected_dim <= 0:
            raise ValueError("VECTOR_DIMENSION must be set to a positive integer")
        if expected_dim and embedding_dim != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim}, got {embedding_dim}"
            )

        # Replace any previous embeddings for this report to avoid unique constraint collisions.
        deleted = delete_report_embeddings_by_report_id(report_id)
        if deleted:
            logger.info(
                "Deleted %d existing embeddings for report_id=%s", deleted, report_id
            )

        create_report_embeddings(
            IReportEmbeddings(report_id=report_id, texts=chunks, embeddings=vectors)
        )

        logger.info("Stored %d embeddings for report_id=%s", len(chunks), report_id)
        return IEmbeddingsAgentOutput(
            rund_id=payload.rund_id,
            status="completed",
            output=IOutputData(
                report_id=report_id,
                chunk_count=len(chunks),
                embedding_dim=embedding_dim,
            ),
        )

    except Exception as e:
        logger.error(
            "Failed to generate/store embeddings for report_id=%s: %s", report_id, e
        )
        return IEmbeddingsAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )
