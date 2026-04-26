"""Tests for db.py local-JSON fallback CRUD."""

import json

import pytest

import db


@pytest.fixture()
def local_db(tmp_path, monkeypatch):
    """Patch db module to use a temporary JSON file."""
    local_file = tmp_path / "timeline.json"
    monkeypatch.setattr(db, "_LOCAL_FILE", local_file)
    monkeypatch.setattr(db, "DATABASE_URL", None)
    return local_file


ENTRY_A = {"date": "2024-01-01", "bodyweight": 64.0, "added_weight": 20.0, "reps": 5}
ENTRY_B = {"date": "2024-02-01", "bodyweight": 65.0, "added_weight": 22.0, "reps": 6}


class TestLocalLoad:
    def test_returns_empty_when_no_file(self, local_db):
        assert db._local_load() == []

    def test_returns_entries_from_file(self, local_db):
        local_db.write_text(json.dumps([ENTRY_A]))
        assert db._local_load() == [ENTRY_A]


class TestLocalAdd:
    def test_creates_file_and_adds_entry(self, local_db):
        db._local_add(ENTRY_A)
        assert local_db.exists()
        data = json.loads(local_db.read_text())
        assert len(data) == 1
        assert data[0] == ENTRY_A

    def test_appends_to_existing(self, local_db):
        db._local_add(ENTRY_A)
        db._local_add(ENTRY_B)
        data = json.loads(local_db.read_text())
        assert len(data) == 2


class TestLocalDelete:
    def test_removes_by_index(self, local_db):
        local_db.write_text(json.dumps([ENTRY_A, ENTRY_B]))
        db._local_delete(0)
        data = json.loads(local_db.read_text())
        assert len(data) == 1
        assert data[0] == ENTRY_B


class TestPublicAPI:
    def test_load_timeline_uses_local(self, local_db):
        db._local_add(ENTRY_A)
        result = db.load_timeline()
        assert result == [ENTRY_A]

    def test_add_timeline_entry_uses_local(self, local_db):
        db.add_timeline_entry(ENTRY_A)
        assert db.load_timeline() == [ENTRY_A]

    def test_delete_timeline_entry_uses_local(self, local_db):
        db.add_timeline_entry(ENTRY_A)
        db.add_timeline_entry(ENTRY_B)
        db.delete_timeline_entry(0)
        assert db.load_timeline() == [ENTRY_B]
