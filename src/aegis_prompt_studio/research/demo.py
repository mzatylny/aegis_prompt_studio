from __future__ import annotations

from aegis_prompt_studio.models import Claim, ResearchPlan, SourceRecord


def demo_plan(question: str) -> ResearchPlan:
    return ResearchPlan(
        objective=f"Produce a balanced, evidence-led answer to: {question}",
        subquestions=[
            "What are the core definitions and mechanisms?",
            "What evidence supports the main claims?",
            "Where do credible sources disagree or show uncertainty?",
            "What practical implications follow from the evidence?",
        ],
        search_queries=[
            f"{question} systematic review",
            f"{question} official guidance",
            f"{question} recent evidence limitations",
            f"{question} expert consensus",
        ],
        evaluation_criteria=[
            "Source authority and primary evidence",
            "Recency and methodological quality",
            "Agreement across independent sources",
            "Clear separation of fact, inference, and uncertainty",
        ],
        risk_notes=["Demo mode uses illustrative sources and does not perform live web retrieval."],
    )


def demo_sources() -> list[SourceRecord]:
    return [
        SourceRecord(
            title="Illustrative primary research record",
            url="https://example.org/primary-research",
            domain="example.org",
            snippet="Placeholder for a primary or peer-reviewed source in live mode.",
            trust_score=0.72,
        ),
        SourceRecord(
            title="Illustrative official guidance",
            url="https://example.gov/guidance",
            domain="example.gov",
            snippet="Placeholder for an official or regulatory source in live mode.",
            trust_score=0.92,
        ),
        SourceRecord(
            title="Illustrative independent review",
            url="https://example.edu/review",
            domain="example.edu",
            snippet="Placeholder for an independent synthesis or systematic review.",
            trust_score=0.92,
        ),
    ]


def demo_claims(sources: list[SourceRecord]) -> list[Claim]:
    return [
        Claim(
            statement="A reliable conclusion should be supported by more than one independent source type.",
            source_ids=[source.id for source in sources[:2]],
            confidence=0.9,
            status="supported",
            notes="Methodological claim used to demonstrate the evidence ledger.",
        ),
        Claim(
            statement="Current evidence may contain gaps that should be stated explicitly.",
            source_ids=[sources[-1].id],
            confidence=0.75,
            status="supported",
            notes="The live pipeline asks the critic and fact-checker to identify these gaps.",
        ),
    ]


def demo_report(question: str, plan: ResearchPlan, sources: list[SourceRecord]) -> str:
    return f"""# Research report

## Question

{question}

## Executive assessment

This run demonstrates the complete orchestration path without calling an external model. The live configuration replaces the illustrative material below with current web evidence, source metadata, a claim ledger, adversarial critique, and a final synthesis.

## Analytical framework

The planner decomposed the question into {len(plan.subquestions)} subquestions and {len(plan.search_queries)} targeted searches. Evidence is evaluated for authority, recency, independence, and methodological quality.

## Findings

1. **Definitions and scope** should be established before comparing claims.
2. **Primary evidence and official guidance** should carry more weight than unattributed summaries.
3. **Contradictory evidence** should be preserved rather than forced into a single conclusion.
4. **Uncertainty** should be visible in both the narrative and claim-level confidence scores.

## Evidence ledger

The demonstration includes {len(sources)} source records. In live mode, each record is extracted from web-search output and attached to claims by identifier.

## Limitations

- No live retrieval was performed.
- The listed URLs are illustrative placeholders.
- The report demonstrates system behaviour, not a factual answer to the submitted question.

## Recommended next step

Set `APP_MODE=live` and provide `OPENAI_API_KEY` to run the same workflow with current sources and model-generated analysis.
"""

