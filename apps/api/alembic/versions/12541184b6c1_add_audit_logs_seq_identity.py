"""add audit_logs seq identity

Revision ID: 12541184b6c1
Revises: 33f25a893516
Create Date: 2026-09-16

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "12541184b6c1"
down_revision: str | None = "33f25a893516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column(
            "seq",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            unique=True,
        ),
    )
    op.create_index("ix_audit_logs_seq", "audit_logs", ["seq"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_seq", table_name="audit_logs")
    op.drop_column("audit_logs", "seq")
