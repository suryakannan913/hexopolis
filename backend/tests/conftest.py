import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Every test gets a throwaway SQLite file so suites never touch the real
    store (and never depend on each other's games)."""
    monkeypatch.setenv("HEXOPOLIS_DB", str(tmp_path / "test.db"))
    yield
