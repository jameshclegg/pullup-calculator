"""Tests for Flask routes in app.py."""

from datetime import date, timedelta

import pytest

from tests.conftest import TEST_PASSWORD, TEST_HASH


def _login(client, password=TEST_PASSWORD):
    return client.post("/login", data={"password": password}, follow_redirects=False)


class TestIndex:
    def test_get_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_post_with_bodyweight(self, client):
        resp = client.post("/", data={"bodyweight": "70"})
        assert resp.status_code == 200
        assert b"70" in resp.data


class TestLogin:
    def test_get_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_wrong_password(self, client):
        resp = client.post("/login", data={"password": "wrong"}, follow_redirects=True)
        assert b"Incorrect password" in resp.data

    def test_correct_password_redirects(self, client):
        resp = _login(client)
        assert resp.status_code == 302
        assert "/timeline" in resp.headers["Location"]

    def test_login_sets_session(self, client):
        _login(client)
        resp = client.get("/timeline")
        assert resp.status_code == 200


class TestLogout:
    def test_logout_clears_session(self, client):
        _login(client)
        client.post("/logout")
        resp = client.get("/timeline")
        assert resp.status_code == 302  # redirected to login


class TestTimeline:
    def test_redirects_when_not_authenticated(self, client):
        resp = client.get("/timeline")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_authenticated_access(self, client):
        _login(client)
        resp = client.get("/timeline")
        assert resp.status_code == 200

    def test_add_valid_entry(self, client, tmp_path, monkeypatch):
        import db, json
        # Pre-populate so the timeline chart trendline has enough data points
        local_file = db._LOCAL_FILE
        seed = [{"date": "2024-04-01", "bodyweight": 64.0, "added_weight": 18.0, "reps": 5}]
        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_text(json.dumps(seed))

        _login(client)
        resp = client.post("/timeline", data={
            "action": "add",
            "date": "2024-06-01",
            "bodyweight": "64",
            "added_weight": "20",
            "reps": "5",
        })
        assert resp.status_code == 200
        assert b"Entry added" in resp.data

    def test_bodyweight_out_of_range(self, client):
        _login(client)
        resp = client.post("/timeline", data={
            "action": "add",
            "date": "2024-06-01",
            "bodyweight": "50",
            "added_weight": "20",
            "reps": "5",
        })
        assert b"Bodyweight must be between 55 and 75" in resp.data

    def test_added_weight_out_of_range(self, client):
        _login(client)
        resp = client.post("/timeline", data={
            "action": "add",
            "date": "2024-06-01",
            "bodyweight": "64",
            "added_weight": "70",
            "reps": "5",
        })
        assert b"Added weight must be between 0 and 65" in resp.data

    def test_reps_out_of_range(self, client):
        _login(client)
        resp = client.post("/timeline", data={
            "action": "add",
            "date": "2024-06-01",
            "bodyweight": "64",
            "added_weight": "20",
            "reps": "50",
        })
        assert b"Reps must be between 1 and 40" in resp.data

    def test_future_date_rejected(self, client):
        _login(client)
        future = (date.today() + timedelta(days=10)).isoformat()
        resp = client.post("/timeline", data={
            "action": "add",
            "date": future,
            "bodyweight": "64",
            "added_weight": "20",
            "reps": "5",
        })
        assert b"Date cannot be in the future" in resp.data
