"""add reply high quality

Revision ID: 7c4e9b12a8d1
Revises: 05113da6ac42
Create Date: 2026-09-18 17:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "7c4e9b12a8d1"
down_revision = "05113da6ac42"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "replies",
        sa.Column(
            "is_high_quality",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("replies", "is_high_quality")
