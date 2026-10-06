import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    return app.test_client()


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_shorten_and_redirect(client):
    resp = client.post("/api/shorten", json={"url": "https://example.com/page"})
    assert resp.status_code == 201
    code = resp.get_json()["code"]
    assert len(code) == 6

    redirect = client.get(f"/{code}")
    assert redirect.status_code == 302
    assert redirect.headers["Location"] == "https://example.com/page"


def test_invalid_url_rejected(client):
    resp = client.post("/api/shorten", json={"url": "javascript:alert(1)"})
    assert resp.status_code == 400


def test_unknown_code_404(client):
    assert client.get("/nope12").status_code == 404


def test_metrics_exposed(client):
    client.get("/healthz")
    body = client.get("/metrics").get_data(as_text=True)
    assert "http_requests_total" in body
