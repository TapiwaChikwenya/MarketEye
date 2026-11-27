"""The production command is `alembic upgrade head` before uvicorn.

That command exits if alembic/versions is missing. The baseline revision
stamps the database and leaves table creation to create_all.
"""
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def test_baseline_revision_is_present_and_has_no_parent():
    matches = list(VERSIONS.glob("*0001_baseline*.py"))
    assert matches, f"expected a baseline revision under {VERSIONS}"
    text = matches[0].read_text(encoding="utf-8")
    assert 'revision = "0001_baseline"' in text
    assert "down_revision = None" in text
    assert "def upgrade" in text
    assert "def downgrade" in text
    assert "op.create" not in text
    assert "op.drop" not in text
