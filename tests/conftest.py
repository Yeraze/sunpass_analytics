import pytest


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = tmp_path / "test_sunpass.db"
    monkeypatch.setattr("sunpass.config.DB_PATH", db_path)
    monkeypatch.setattr("sunpass.config.DATA_DIR", tmp_path)
    # Also patch the imported binding in models.py
    monkeypatch.setattr("sunpass.db.models.DB_PATH", db_path)
    return db_path
