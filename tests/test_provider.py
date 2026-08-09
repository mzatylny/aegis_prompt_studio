import re

import pytest

from aegis_prompt_studio.config import Settings
from aegis_prompt_studio.models import Claim, ResearchPlan, ResearchQuestion
from aegis_prompt_studio.research.provider import (
    ClaimLedger,
    OpenAIResearchProvider,
)


class FakeResponse:
    def __init__(self, *, output_text: str = "", output_parsed=None, payload=None) -> None:
        self.output_text = output_text
        self.output_parsed = output_parsed
        self.payload = payload or {}

    def model_dump(self, mode: str = "json") -> dict:
        assert mode == "json"
        return self.payload


class FakeResponses:
    def __init__(self, plan: ResearchPlan) -> None:
        self.plan = plan
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["text_format"] is ResearchPlan:
            return FakeResponse(output_parsed=self.plan)
        return FakeResponse(output_parsed=ClaimLedger())

    def create(self, **kwargs):
        self.calls.append(kwargs)
        prompt = kwargs["input"]
        if kwargs.get("tools"):
            return FakeResponse(
                output_text="Evidence dossier",
                payload={
                    "sources": [
                        {
                            "title": "Recent official guidance",
                            "url": "https://example.gov/recent",
                            "published_at": "2026-07-01",
                        },
                        {
                            "title": "Old official guidance",
                            "url": "https://example.gov/old",
                            "published_at": "2020-01-01",
                        },
                    ]
                },
            )
        if "adversarial critic" in prompt:
            return FakeResponse(output_text="Demand stronger evidence.")
        source_id = re.search(r"\[([0-9a-f]{10})\]", prompt)
        citation = f" [{source_id.group(1)}]" if source_id else ""
        return FakeResponse(output_text=f"# Report\n\nVerified finding.{citation}")


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def make_provider() -> tuple[OpenAIResearchProvider, FakeResponses]:
    plan = ResearchPlan(
        objective="Evaluate the evidence",
        subquestions=["What happened?", "What supports it?"],
        search_queries=["official evidence", "independent evidence"],
        evaluation_criteria=["authority", "recency"],
    )
    responses = FakeResponses(plan)
    provider = object.__new__(OpenAIResearchProvider)
    provider.settings = Settings(APP_MODE="live", OPENAI_API_KEY="test-key")
    provider.client = FakeClient(responses)
    return provider, responses


def test_live_provider_applies_recency_and_domain_policy() -> None:
    provider, responses = make_provider()
    request = ResearchQuestion(
        question="What does the current official evidence show?",
        allowed_domains=["example.gov"],
        require_recent_sources=True,
    )
    plan = provider.plan(request)
    evidence = provider.research(request, plan)

    assert [source.title for source in evidence.sources] == ["Recent official guidance"]
    research_call = next(call for call in responses.calls if call.get("tools"))
    assert research_call["tools"][0]["filters"]["allowed_domains"] == ["example.gov"]
    assert "last two years" in research_call["input"]


def test_live_provider_runs_critic_fact_checker_and_writer() -> None:
    provider, _ = make_provider()
    request = ResearchQuestion(question="What does current evidence show?")
    plan = provider.plan(request)
    evidence = provider.research(request, plan)
    critique = provider.critique(request, evidence)
    ledger = provider.fact_check(request, evidence, critique)
    source = evidence.sources[0]
    ledger = ClaimLedger(
        claims=[
            Claim(
                statement="A verified finding",
                source_ids=[source.id],
                confidence=0.9,
                status="supported",
            )
        ]
    )
    report = provider.write_report(request, plan, evidence, critique, ledger)

    assert critique == "Demand stronger evidence."
    assert isinstance(ledger, ClaimLedger)
    assert f"[{source.id}]" in report


def test_live_provider_requires_an_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIResearchProvider(Settings(APP_MODE="live", OPENAI_API_KEY=None))
