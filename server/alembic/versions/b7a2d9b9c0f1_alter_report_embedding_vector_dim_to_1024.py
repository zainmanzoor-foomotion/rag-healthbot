"""Alter report_embedding.embedding to vector(1024)

Revision ID: b7a2d9b9c0f1
Revises: f5db3ce475b5
Create Date: 2026-02-26

Notes:
- The original migration created embedding as vector(332).
- This migration deletes any existing embeddings and changes the column type
  to vector(1024), then recreates the HNSW index.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7a2d9b9c0f1"
down_revision: Union[str, Sequence[str], None] = "f5db3ce475b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_DIM = 332
NEW_DIM = 1024
TABLE = "report_embedding"
INDEX = "idx_embedding_hnsw"


def upgrade() -> None:
    # Existing rows (if any) will have the old dimension; safest is to delete
    # and regenerate embeddings.
    op.execute(f"DELETE FROM {TABLE}")

    # Drop and recreate the HNSW index around the type change.
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")

    op.execute(
        f"ALTER TABLE {TABLE} "
        f"ALTER COLUMN embedding TYPE vector({NEW_DIM}) "
        f"USING embedding::vector({NEW_DIM})"
    )

    op.execute(
        f"CREATE INDEX {INDEX} ON {TABLE} " f"USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM {TABLE}")
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")

    op.execute(
        f"ALTER TABLE {TABLE} "
        f"ALTER COLUMN embedding TYPE vector({OLD_DIM}) "
        f"USING embedding::vector({OLD_DIM})"
    )

    op.execute(
        f"CREATE INDEX {INDEX} ON {TABLE} " f"USING hnsw (embedding vector_cosine_ops)"
    )
