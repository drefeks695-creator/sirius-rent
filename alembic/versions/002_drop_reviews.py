"""Drop reviews table.

Revision ID: 002_drop_reviews
Revises: 001_baseline
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_drop_reviews"
down_revision: Union[str, None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reviews")


def downgrade() -> None:
    pass
