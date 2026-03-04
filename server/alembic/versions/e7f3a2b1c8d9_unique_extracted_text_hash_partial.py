"""Add partial unique index on report.extracted_text_hash (WHERE NOT NULL)

Without this, uploading the same file when content_hash is NULL (e.g. when the
base64 decode step fails) lets create_report insert a second Report row for
identical content, causing non-deterministic entity counts and orphaned link rows.

Revision ID: e7f3a2b1c8d9
Revises: 94e89ecc4829
Create Date: 2026-03-02
"""

from alembic import op

revision = "e7f3a2b1c8d9"
down_revision = "94e89ecc4829"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index prevents duplicate non-NULL extracted_text_hash values.
    # PostgreSQL treats NULL as distinct in plain UNIQUE constraints, so a plain
    # unique index on a nullable column would still allow multiple NULL rows.
    # The WHERE clause restricts the uniqueness guarantee to populated rows only.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_extracted_text_hash_notnull
        ON report (extracted_text_hash)
        WHERE extracted_text_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_report_extracted_text_hash_notnull")
