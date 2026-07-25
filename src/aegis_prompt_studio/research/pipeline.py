from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from aegis_prompt_studio.config import Settings, get_settings
from aegis_prompt_studio.models import (
    AgentTrace,
    Claim,
    ResearchPlan,
    ResearchQuestion,
    ResearchResult,
    SourceRecord,
)
from aegis_prompt_studio.research.demo import demo_claims, demo_plan, demo_report, demo_sources
from aegis_prompt_studio.research.provider import ClaimLedger, OpenAIResearchProvider, WebEvidence
from aegis_prompt_studio.security.scanner import PromptSecurityScanner


def now() -> datetime:
    return datetime.now(UTC)


@dataclass
class StageOutput:
    value: object
    trace: AgentTrace


class ResearchPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.security = PromptSecurityScanner(max_chars=self.settings.max_input_chars)

    def run(self, request: ResearchQuestion) -> ResearchResult:
        started = perf_counter()
        traces: list[AgentTrace] = []
        security_result = self.security.scan(request.question)

        if self.settings.live_enabled:
            result = self._run_live(request, traces)
        else:
            result = self._run_demo(request, traces)

        result.trace = traces
        result.metrics.update(
            {
                "elapsed_seconds": round(perf_counter() - started, 3),
                "source_count": len(result.sources),
                "claim_count": len(result.claims),
                "agent_count": len(traces),
                "input_security_score": security_result.risk_score,
                **self._evidence_metrics(result),
            }
        )
        result.quality_score = self._quality_score(result)
        if security_result.risk_score >= 65:
            result.limitations.insert(
                0,
                "The submitted topic contained high-risk prompt-injection indicators and was treated strictly as untrusted data.",
            )
        return result

    def _stage(self, agent: str, input_summary: str, fn: Callable[[], object]) -> StageOutput:
        started = now()
        value = fn()
        finished = now()
        output_summary = self._summarize(value)
        return StageOutput(
            value=value,
            trace=AgentTrace(
                agent=agent,
                status="completed",
                started_at=started,
                finished_at=finished,
                input_summary=input_summary[:500],
                output_summary=output_summary[:800],
            ),
        )

    def _run_live(self, request: ResearchQuestion, traces: list[AgentTrace]) -> ResearchResult:
        provider = OpenAIResearchProvider(self.settings)

        planner = self._stage("planner", request.question, lambda: provider.plan(request))
        traces.append(planner.trace)
        plan = planner.value
        assert isinstance(plan, ResearchPlan)

        researcher = self._stage("researcher", plan.objective, lambda: provider.research(request, plan))
        traces.append(researcher.trace)
        evidence = researcher.value
        assert isinstance(evidence, WebEvidence)

        critic = self._stage("critic", evidence.text[:1000], lambda: provider.critique(request, evidence))
        traces.append(critic.trace)
        critique = str(critic.value)

        checker = self._stage(
            "fact_checker",
            critique[:1000],
            lambda: provider.fact_check(request, evidence, critique),
        )
        traces.append(checker.trace)
        ledger = checker.value
        assert isinstance(ledger, ClaimLedger)
        ledger = self._validate_ledger(ledger, evidence.sources)

        writer = self._stage(
            "writer",
            f"{len(ledger.claims)} claims and {len(evidence.sources)} sources",
            lambda: provider.write_report(request, plan, evidence, critique, ledger),
        )
        traces.append(writer.trace)
        report = str(writer.value)

        executive = self._extract_executive_summary(report)
        limitations = ledger.limitations or [
            "The report is limited by the coverage and accessibility of web sources returned during this run."
        ]
        return ResearchResult(
            mode="live",
            question=request.question,
            plan=plan,
            executive_summary=executive,
            report_markdown=report,
            sources=evidence.sources,
            claims=ledger.claims,
            limitations=limitations,
            trace=traces,
            quality_score=0,
            metrics={"depth": request.depth, "style": request.output_style},
        )

    def _run_demo(self, request: ResearchQuestion, traces: list[AgentTrace]) -> ResearchResult:
        planner = self._stage("planner", request.question, lambda: demo_plan(request.question))
        traces.append(planner.trace)
        plan = planner.value
        assert isinstance(plan, ResearchPlan)

        researcher = self._stage("researcher", plan.objective, demo_sources)
        traces.append(researcher.trace)
        sources = researcher.value
        assert isinstance(sources, list)

        critic = self._stage(
            "critic",
            "Illustrative evidence dossier",
            lambda: "Demo review: verify every material claim against live primary sources before use.",
        )
        traces.append(critic.trace)

        checker = self._stage("fact_checker", str(critic.value), lambda: demo_claims(sources))
        traces.append(checker.trace)
        claims = checker.value
        assert isinstance(claims, list)

        writer = self._stage(
            "writer",
            f"{len(claims)} claims and {len(sources)} illustrative sources",
            lambda: demo_report(request.question, plan, sources),
        )
        traces.append(writer.trace)
        report = str(writer.value)

        return ResearchResult(
            mode="demo",
            question=request.question,
            plan=plan,
            executive_summary=(
                "The full multi-agent workflow completed in demo mode. Configure a live API key to replace "
                "illustrative evidence with current web sources."
            ),
            report_markdown=report,
            sources=sources,
            claims=claims,
            limitations=[
                "Demo mode does not retrieve current information.",
                "Illustrative source URLs are placeholders and must not be cited as evidence.",
            ],
            trace=traces,
            quality_score=0,
            metrics={"depth": request.depth, "style": request.output_style},
        )

    @staticmethod
    def _summarize(value: object) -> str:
        if isinstance(value, ResearchPlan):
            return f"Plan with {len(value.subquestions)} subquestions and {len(value.search_queries)} searches."
        if isinstance(value, WebEvidence):
            return f"Evidence dossier with {len(value.sources)} sources and {len(value.text)} characters."
        if isinstance(value, ClaimLedger):
            return f"Claim ledger with {len(value.claims)} claims and {len(value.limitations)} limitations."
        if isinstance(value, list):
            return f"Produced {len(value)} items."
        text = str(value).replace("\n", " ")
        return text[:800]

    @staticmethod
    def _extract_executive_summary(report: str) -> str:
        lines = [line.strip() for line in report.splitlines()]
        collecting = False
        collected: list[str] = []
        for line in lines:
            if line.lower().lstrip("# ") in {"executive summary", "executive assessment"}:
                collecting = True
                continue
            if collecting and line.startswith("#"):
                break
            if collecting and line:
                collected.append(line)
        return " ".join(collected)[:1800] or report[:1800]

    @staticmethod
    def _validate_ledger(ledger: ClaimLedger, sources: list[SourceRecord]) -> ClaimLedger:
        """Remove hallucinated source references before claims reach the writer."""
        valid_ids = {source.id for source in sources}
        validated: list[Claim] = []
        for original in ledger.claims:
            claim = original.model_copy(deep=True)
            unknown_ids = [source_id for source_id in claim.source_ids if source_id not in valid_ids]
            claim.source_ids = [source_id for source_id in claim.source_ids if source_id in valid_ids]
            if unknown_ids:
                suffix = f"Removed unknown source IDs: {', '.join(unknown_ids)}."
                claim.notes = f"{claim.notes} {suffix}".strip()
            if not claim.source_ids:
                claim.status = "unsupported"
                claim.confidence = min(claim.confidence, 0.2)
                claim.notes = (
                    f"{claim.notes} No verified source reference supports this claim."
                ).strip()
            validated.append(claim)
        return ledger.model_copy(update={"claims": validated}, deep=True)

    @staticmethod
    def _evidence_metrics(result: ResearchResult) -> dict[str, int | float | str]:
        source_ids = {source.id for source in result.sources}
        total = len(result.claims)
        cited = sum(
            1
            for claim in result.claims
            if claim.source_ids and all(source_id in source_ids for source_id in claim.source_ids)
        )
        supported = sum(1 for claim in result.claims if claim.status == "supported")
        return {
            "citation_integrity_percent": round((cited / total) * 100, 1) if total else 100.0,
            "supported_claim_percent": round((supported / total) * 100, 1) if total else 0.0,
            "unique_source_domains": len({source.domain for source in result.sources}),
        }

    @staticmethod
    def _quality_score(result: ResearchResult) -> int:
        if result.mode == "demo":
            return 72
        source_score = min(25, len(result.sources) * 3)
        trusted_score = min(15, int(sum(source.trust_score for source in result.sources) * 2))
        claim_score = min(20, sum(4 for claim in result.claims if claim.status == "supported"))
        integrity_score = round(
            15 * float(result.metrics.get("citation_integrity_percent", 0)) / 100
        )
        uncertainty_score = 10 if result.limitations else 0
        workflow_score = min(15, len(result.trace) * 3)
        return min(
            100,
            source_score
            + trusted_score
            + claim_score
            + integrity_score
            + uncertainty_score
            + workflow_score,
        )
