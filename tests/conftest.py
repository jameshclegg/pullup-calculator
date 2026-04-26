"""Shared fixtures for the pull-up calculator test suite."""

import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_PASSWORD = "testpass"
TEST_HASH = generate_password_hash(TEST_PASSWORD)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client with local-JSON DB patched to a temp directory."""
    import db
    import app as app_module

    local_file = tmp_path / "timeline.json"
    monkeypatch.setattr(db, "DATABASE_URL", None)
    monkeypatch.setattr(db, "_LOCAL_FILE", local_file)
    monkeypatch.setattr(app_module, "PASSWORD_HASH", TEST_HASH)

    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as c:
        yield c
