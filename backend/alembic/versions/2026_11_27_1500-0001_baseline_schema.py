"""Baseline so production can run ``alembic upgrade head``.

The production compose command is ``alembic upgrade head && uvicorn ...``.
Without a ``versions/`` directory that command exits before the API starts.
Tables are still created by ``Base.metadata.create_all`` on application
startup. This revision only stamps ``alembic_version`` so a later migration
has a parent. It does not create or drop tables.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-27
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Stamp the existing create_all schema. No DDL."""


def downgrade() -> None:
    """Drop the stamp only. Application tables stay."""
