"""add calculation_method and manual_points to reports

Revision ID: a1b2c3d4e5f6
Revises: 12541184b6c1
Create Date: 2026-09-17
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "12541184b6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "calculation_method",
            sa.String(length=10),
            nullable=False,
            server_default="auto",
        ),
    )
    op.add_column(
        "reports",
        sa.Column("manual_points", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "manual_points")
    op.drop_column("reports", "calculation_method")
