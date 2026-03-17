"""Add device_heartbeats

Revision ID: 0c1d2e3f4a5b
Revises: 7a4dbd63b733
Create Date: 2026-03-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0c1d2e3f4a5b"
down_revision: Union[str, None] = "7a4dbd63b733"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_heartbeats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False),
        sa.Column("port", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("device_heartbeats")

