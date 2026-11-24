import pytest
from fastapi.testclient import TestClient

from tracker.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GENCHI_DB", str(tmp_path / "test.db"))
    return TestClient(app)


def make(client, source="direct", email="a@example.com"):
    r = client.post(
        "/requests",
        json={"name": "A", "email": email, "source": source, "use_case": "shop assist"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def advance(client, rid, *stages):
    for s in stages:
        assert client.post(f"/requests/{rid}/stage", json={"stage": s}).status_code == 200


def test_create_defaults_to_enquiry(client):
    rid = make(client)
    body = client.get(f"/requests/{rid}").json()
    assert body["stage"] == "enquiry"
    assert body["source"] == "direct"


def test_rejects_bad_email(client):
    r = client.post("/requests", json={"name": "A", "email": "nope", "use_case": "x"})
    assert r.status_code == 422


def test_missing_request_is_404(client):
    assert client.get("/requests/99").status_code == 404


def test_stage_cannot_move_backwards_or_repeat(client):
    rid = make(client)
    advance(client, rid, "booked")
    assert client.post(f"/requests/{rid}/stage", json={"stage": "qualified"}).status_code == 409
    assert client.post(f"/requests/{rid}/stage", json={"stage": "booked"}).status_code == 409


def test_unknown_stage_rejected(client):
    rid = make(client)
    assert client.post(f"/requests/{rid}/stage", json={"stage": "refunded"}).status_code == 422


def test_skipped_stage_counts_only_when_reached(client):
    rid = make(client)
    advance(client, rid, "booked")
    counts = client.get("/funnel").json()["counts"]
    assert counts == {"enquiry": 1, "qualified": 0, "booked": 1, "completed": 0, "paid": 0}


def test_funnel_rates(client):
    a, b, c, d = (make(client, email=f"{i}@example.com") for i in range(4))
    advance(client, a, "qualified", "booked", "completed", "paid")
    advance(client, b, "qualified", "booked")
    advance(client, c, "qualified")
    data = client.get("/funnel").json()
    assert data["counts"] == {"enquiry": 4, "qualified": 3, "booked": 2, "completed": 1, "paid": 1}
    rates = {(s["from"], s["to"]): s["rate"] for s in data["steps"]}
    assert rates[("enquiry", "qualified")] == 0.75
    assert rates[("qualified", "booked")] == 0.6667
    assert rates[("booked", "completed")] == 0.5
    assert rates[("completed", "paid")] == 1.0
    assert data["overall"] == 0.25


def test_empty_funnel_has_no_rates(client):
    data = client.get("/funnel").json()
    assert data["overall"] is None
    assert all(s["rate"] is None for s in data["steps"])


def test_funnel_by_source(client):
    a = make(client, source="instagram")
    make(client, source="instagram", email="b@example.com")
    c = make(client, source="event", email="c@example.com")
    advance(client, a, "qualified", "booked", "completed", "paid")
    advance(client, c, "qualified")
    by = client.get("/funnel/by-source").json()
    assert by["instagram"]["overall"] == 0.5
    assert by["event"]["overall"] == 0.0
    assert client.get("/funnel", params={"source": "instagram"}).json()["counts"]["paid"] == 1


def test_list_filters(client):
    a = make(client, source="instagram")
    make(client, source="event", email="b@example.com")
    advance(client, a, "qualified")
    assert len(client.get("/requests").json()) == 2
    assert len(client.get("/requests", params={"source": "event"}).json()) == 1
    assert len(client.get("/requests", params={"stage": "qualified"}).json()) == 1
