"""Add report content/extracted_text hashes for dedup

Revision ID: c3e1a4f2d7ab
Revises: b7a2d9b9c0f1
Create Date: 2026-02-26

Adds:
- report.content_hash (unique, nullable)        : md5(file bytes)
- report.extracted_text_hash (indexed, nullable): md5(extracted_text)

Also backfills extracted_text_hash for existing rows using Postgres `md5(text)`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3e1a4f2d7ab"
down_revision: Union[str, Sequence[str], None] = "b7a2d9b9c0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report",
        sa.Column("content_hash", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "report",
        sa.Column("extracted_text_hash", sa.String(length=32), nullable=True),
    )

    op.create_index(
        "ix_report_content_hash",
        "report",
        ["content_hash"],
        unique=True,
    )
    op.create_index(
        "ix_report_extracted_text_hash",
        "report",
        ["extracted_text_hash"],
        unique=False,
    )

    # Backfill for existing rows where extracted_text exists.
    op.execute(
        """
        UPDATE report
        SET extracted_text_hash = md5(extracted_text)
        WHERE extracted_text IS NOT NULL
          AND extracted_text_hash IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_report_extracted_text_hash", table_name="report")
    op.drop_index("ix_report_content_hash", table_name="report")

    op.drop_column("report", "extracted_text_hash")
    op.drop_column("report", "content_hash")
