"""add customer soft delete flag

Revision ID: 20260617_add_customer_is_deleted
Revises:
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_add_customer_is_deleted"
down_revision: str | Sequence[str] | None = "84ecaf6fdf73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("customers", "is_deleted", server_default=None)


def downgrade() -> None:
    op.drop_column("customers", "is_deleted")
