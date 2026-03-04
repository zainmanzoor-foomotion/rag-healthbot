"""
Index ICD-10-CM and CPT code descriptions as vector embeddings.

Reads the local ICD-10-CM and CPT files, embeds every description via
Ollama, and stores the vectors in the ``code_embedding`` table for
semantic KB search.

Usage (via CLI entry-point defined in pyproject.toml):
    uv run index-codes           # index both ICD-10 and CPT
    uv run index-codes --icd10   # only ICD-10
    uv run index-codes --cpt     # only CPT
    uv run index-codes --force   # drop existing embeddings first
"""

from __future__ import annotations

import csv
import io
import logging
import sys
import time

from langchain_ollama import OllamaEmbeddings

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.db.CodeEmbeddingRepo import (
    count_code_embeddings,
    delete_all_code_embeddings,
    upsert_code_embeddings,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 128  # texts per Ollama call


# ── File readers ──────────────────────────────────────────────────────


def _read_icd10(path: str) -> list[tuple[str, str]]:
    """Return list of (code, description) from the ICD-10-CM tab-separated file."""
    pairs: list[tuple[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if "\t" in line:
                code, desc = line.split("\t", 1)
            else:
                code, desc = line[:7].strip(), line[7:].strip()
            code = code.strip().replace(".", "")
            desc = desc.strip()
            if code and desc:
                pairs.append((code, desc))
    return pairs


def _read_cpt(path: str) -> list[tuple[str, str]]:
    """Return list of (code, description) from the CPT CSV file."""
    pairs: list[tuple[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    reader = csv.reader(io.StringIO(content))
    for row in reader:
        if len(row) < 2:
            continue
        code = row[0].strip().strip('"')
        desc = row[1].strip().strip('"')
        if code and desc and not code.upper().startswith("CODE") and code[0].isdigit():
            pairs.append((code, desc))
    return pairs


# ── Embedding + storage ──────────────────────────────────────────────


def _make_embedder() -> OllamaEmbeddings:
    if not settings.ollama_host or not settings.ollama_embed_model:
        raise ValueError("OLLAMA_HOST and OLLAMA_EMBED_MODEL must be set")
    return OllamaEmbeddings(
        base_url=settings.ollama_host, model=settings.ollama_embed_model
    )


def index_codes(
    code_system: str,
    pairs: list[tuple[str, str]],
    force: bool = False,
) -> int:
    """
    Embed and store code descriptions for one code system.

    Parameters
    ----------
    code_system : str   – "icd10" or "cpt"
    pairs       : list  – [(code, description), ...]
    force       : bool  – drop existing embeddings first

    Returns
    -------
    int – number of new embeddings stored
    """
    existing = count_code_embeddings(code_system)
    if existing and not force:
        logger.info(
            "  %s already has %d embeddings – skipping (use --force to re-index)",
            code_system,
            existing,
        )
        return 0

    if force and existing:
        logger.info("  Dropping %d existing %s embeddings", existing, code_system)
        delete_all_code_embeddings(code_system)

    embedder = _make_embedder()
    total = len(pairs)
    stored = 0
    t0 = time.time()

    for start in range(0, total, BATCH_SIZE):
        batch = pairs[start : start + BATCH_SIZE]
        descs = [d for _, d in batch]

        try:
            vectors = embedder.embed_documents(descs)
        except Exception:
            logger.exception(
                "  Embedding batch %d–%d failed", start, start + len(batch)
            )
            continue

        rows = [
            {
                "code": code,
                "code_system": code_system,
                "description": desc,
                "embedding": vec,
            }
            for (code, desc), vec in zip(batch, vectors)
        ]
        inserted = upsert_code_embeddings(rows)
        stored += inserted

        elapsed = time.time() - t0
        pct = min(100, (start + len(batch)) / total * 100)
        print(
            f"\r  [{code_system}] {start + len(batch):>6}/{total}  "
            f"({pct:5.1f}%)  {elapsed:.0f}s",
            end="",
            flush=True,
        )

    print()  # newline after progress
    logger.info(
        "  Stored %d %s embeddings in %.1fs", stored, code_system, time.time() - t0
    )
    return stored


# ── CLI entry-point ───────────────────────────────────────────────────


def index_codes_cli():
    """CLI entry-point: embed ICD-10-CM and/or CPT code descriptions."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    args = set(sys.argv[1:])
    force = "--force" in args
    do_icd10 = "--icd10" in args or not (args - {"--force"})
    do_cpt = "--cpt" in args or not (args - {"--force"})

    total_stored = 0

    if do_icd10:
        path = settings.icd10_file
        if not path:
            print("ERROR: ICD10_FILE not configured", file=sys.stderr)
            sys.exit(1)
        print(f"Reading ICD-10-CM codes from {path}")
        pairs = _read_icd10(path)
        print(f"  Found {len(pairs)} codes")
        total_stored += index_codes("icd10", pairs, force=force)

    if do_cpt:
        path = settings.cpt_file
        if not path:
            print("ERROR: CPT_FILE not configured", file=sys.stderr)
            sys.exit(1)
        print(f"Reading CPT codes from {path}")
        pairs = _read_cpt(path)
        print(f"  Found {len(pairs)} codes")
        total_stored += index_codes("cpt", pairs, force=force)

    print(f"\nDone. Total embeddings stored: {total_stored}")
    sys.exit(0)
