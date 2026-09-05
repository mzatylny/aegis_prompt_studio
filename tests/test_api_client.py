import httpx
import pytest
from fastapi.testclient import TestClient

from aegis_prompt_studio import api
from aegis_prompt_studio.api_client import ResearchRequestError, request_research
from aegis_prompt_studio.models import ResearchQuestion


def bridge(monkeypatch):
    client = TestClient(api.app)

    def post(url, *, json, headers, timeout):
        assert url == "http://research/v1/research/run"
        assert timeout == 600.0
        return client.post("/v1/research/run", json=json, headers=headers)

    monkeypatch.setattr(httpx, "post", post)


def test_ui_client_obeys_api_authentication_and_shared_capacity(monkeypatch):
    bridge(monkeypatch)
    monkeypatch.setattr(api.settings, "api_access_key", "fixture-key")
    question = ResearchQuestion(question="How should research be evaluated?")
    for key in ("", "wrong"):
        with pytest.raises(ResearchRequestError, match="valid access key"):
            request_research(question, base_url="http://research", access_key=key)
    result = request_research(question, base_url="http://research/", access_key="fixture-key")
    assert result.mode == "demo"
    acquired = 0
    try:
        while api.research_slots.acquire(blocking=False):
            acquired += 1
        with pytest.raises(ResearchRequestError, match="capacity is full"):
            request_research(question, base_url="http://research", access_key="fixture-key")
    finally:
        for _ in range(acquired):
            api.research_slots.release()


@pytest.mark.parametrize("status", [503, 502])
def test_ui_client_redacts_service_errors(monkeypatch, status):
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(status, text="secret"))
    with pytest.raises(ResearchRequestError) as error:
        request_research(ResearchQuestion(question="A research question"), base_url="http://research")
    assert "secret" not in str(error.value)


def test_ui_client_redacts_connection_errors_and_malformed_responses(monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("secret connection details")

    monkeypatch.setattr(httpx, "post", unavailable)
    question = ResearchQuestion(question="A research question")
    with pytest.raises(ResearchRequestError, match="unavailable"):
        request_research(question, base_url="http://research")
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(200, json={}))
    with pytest.raises(ResearchRequestError, match="invalid result"):
        request_research(question, base_url="http://research")
