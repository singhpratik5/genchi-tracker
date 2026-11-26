import csv
import io

import pytest
from fastapi.testclient import TestClient

from tracker.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GENCHI_DB", str(tmp_path / "test.db"))
    return TestClient(app)


def make(client, source, email, use_case="shop assist"):
    r = client.post(
        "/requests",
        json={"name": "A", "email": email, "source": source, "use_case": use_case},
    )
    return r.json()["id"]


def rows(response):
    return list(csv.reader(io.StringIO(response.text)))


def test_requests_csv_omits_personal_fields(client):
    make(client, "instagram", "a@example.com")
    resp = client.get("/export/requests.csv")
    assert resp.headers["content-type"].startswith("text/csv")
    data = rows(resp)
    assert data[0] == ["id", "created_at", "country", "source", "use_case", "stage"]
    assert "a@example.com" not in resp.text
    assert data[1][3] == "instagram"


def test_funnel_csv_has_all_row_and_per_source(client):
    a = make(client, "instagram", "a@example.com")
    make(client, "event", "b@example.com")
    for stage in ["qualified", "booked", "completed", "paid"]:
        client.post(f"/requests/{a}/stage", json={"stage": stage})
    data = rows(client.get("/export/funnel.csv"))
    assert data[0] == ["source", "enquiry", "qualified", "booked", "completed", "paid", "overall_rate"]
    by = {r[0]: r for r in data[1:]}
    assert by["all"][1:] == ["2", "1", "1", "1", "1", "0.5"]
    assert by["instagram"][-1] == "1.0"
    assert by["event"][-1] == "0.0"


def test_formula_like_text_is_neutralised(client):
    make(client, "direct", "a@example.com", use_case="=HYPERLINK(1)")
    data = rows(client.get("/export/requests.csv"))
    assert data[1][4] == "'=HYPERLINK(1)"


def test_empty_funnel_csv(client):
    data = rows(client.get("/export/funnel.csv"))
    assert data[1] == ["all", "0", "0", "0", "0", "0", ""]
