"""Baseline columns for existing SQLite databases.

Revision ID: 001_baseline
Revises:
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op

from app.db_migrate import apply_pending_migrations

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    apply_pending_migrations(op.get_bind().engine)


def downgrade() -> None:
    pass
