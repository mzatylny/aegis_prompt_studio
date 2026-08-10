from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aegis_prompt_studio.config import get_settings
from aegis_prompt_studio.models import ResearchQuestion, SecurityScanRequest
from aegis_prompt_studio.research.pipeline import ResearchConfigurationError, ResearchPipeline
from aegis_prompt_studio.security.evaluation import evaluate_scanner
from aegis_prompt_studio.security.report import export_html, export_json
from aegis_prompt_studio.security.scanner import PromptSecurityScanner

app = typer.Typer(help="Aegis Prompt Studio command line interface.")
console = Console()


@app.command()
def scan(
    text: Annotated[str, typer.Argument(help="Prompt or document text to inspect.")],
    json_out: Annotated[Path | None, typer.Option("--json-out")] = None,
    html_out: Annotated[Path | None, typer.Option("--html-out")] = None,
) -> None:
    try:
        result = PromptSecurityScanner(max_chars=get_settings().max_input_chars).scan(
            SecurityScanRequest(text=text)
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="text") from exc
    console.print(Panel(result.summary, title="Security scan"))
    table = Table("Severity", "Category", "Evidence", "Remediation")
    for finding in result.findings:
        table.add_row(
            finding.severity.value,
            finding.category.value,
            finding.evidence,
            finding.remediation,
        )
    console.print(table)
    if json_out:
        export_json(result, json_out)
        console.print(f"JSON report: {json_out}")
    if html_out:
        export_html(result, html_out)
        console.print(f"HTML report: {html_out}")


@app.command()
def research(
    question: Annotated[str, typer.Argument()],
    depth: Annotated[str, typer.Option()] = "standard",
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    try:
        result = ResearchPipeline().run(ResearchQuestion(question=question, depth=depth))
    except ResearchConfigurationError as exc:
        raise typer.ClickException(str(exc)) from exc
    console.print(Panel(result.executive_summary, title=f"Research ({result.mode})"))
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.report_markdown, encoding="utf-8")
        metadata = output.with_suffix(".json")
        metadata.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
        console.print(f"Report: {output}\nMetadata: {metadata}")
    else:
        console.print(result.report_markdown)


@app.command()
def evaluate(
    dataset: Annotated[Path | None, typer.Option("--dataset")] = None,
    risk_threshold: Annotated[int, typer.Option("--risk-threshold", min=0, max=100)] = 12,
    min_precision: Annotated[float, typer.Option("--min-precision", min=0, max=1)] = 0.9,
    min_recall: Annotated[float, typer.Option("--min-recall", min=0, max=1)] = 0.9,
    min_f1: Annotated[float, typer.Option("--min-f1", min=0, max=1)] = 0.9,
    json_out: Annotated[Path | None, typer.Option("--json-out")] = None,
) -> None:
    """Run the versioned scanner benchmark and enforce quality thresholds."""
    report = evaluate_scanner(dataset_path=dataset, risk_threshold=risk_threshold)
    summary = Table("Metric", "Result")
    summary.add_row("Dataset", report.dataset_version)
    summary.add_row("Cases", str(report.total_cases))
    summary.add_row("Precision", f"{report.precision:.1%}")
    summary.add_row("Recall", f"{report.recall:.1%}")
    summary.add_row("Specificity", f"{report.specificity:.1%}")
    summary.add_row("F1", f"{report.f1:.1%}")
    summary.add_row("Failures", str(len(report.failures)))
    console.print(summary)

    category_table = Table("Category", "Recall")
    for category, recall in report.per_category_recall.items():
        category_table.add_row(category, f"{recall:.1%}")
    console.print(category_table)

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"Evaluation report: {json_out}")

    if not report.meets_policy(min_precision, min_recall, min_f1):
        console.print("[red]Evaluation policy failed.[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Evaluation policy passed.[/green]")


if __name__ == "__main__":
    app()
