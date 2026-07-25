from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aegis_prompt_studio.models import ResearchQuestion, SecurityScanRequest
from aegis_prompt_studio.research.pipeline import ResearchPipeline
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
    result = PromptSecurityScanner().scan(SecurityScanRequest(text=text))
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
    result = ResearchPipeline().run(ResearchQuestion(question=question, depth=depth))
    console.print(Panel(result.executive_summary, title=f"Research ({result.mode})"))
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.report_markdown, encoding="utf-8")
        metadata = output.with_suffix(".json")
        metadata.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
        console.print(f"Report: {output}\nMetadata: {metadata}")
    else:
        console.print(result.report_markdown)


if __name__ == "__main__":
    app()

