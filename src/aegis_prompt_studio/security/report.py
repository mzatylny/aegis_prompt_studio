from __future__ import annotations

import html
import json
from pathlib import Path

from aegis_prompt_studio.models import SecurityScanResult


def export_json(result: SecurityScanResult, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return destination


def export_html(result: SecurityScanResult, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(
        f"<tr><td>{html.escape(f.severity.value)}</td><td>{html.escape(f.category.value)}</td>"
        f"<td>{html.escape(f.title)}</td><td><code>{html.escape(f.evidence)}</code></td>"
        f"<td>{html.escape(f.remediation)}</td></tr>"
        for f in result.findings
    )
    payload = html.escape(json.dumps(result.metrics, ensure_ascii=False, indent=2))
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Prompt Security Report</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;background:#0b1020;color:#e8ecf7}}
.card{{background:#131a2d;border:1px solid #29324b;border-radius:16px;padding:24px;margin:18px 0}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #29324b;vertical-align:top}}
code,pre{{white-space:pre-wrap;background:#0a0f1d;padding:4px 7px;border-radius:6px}} .score{{font-size:48px;font-weight:800}}
</style></head><body>
<h1>Prompt Security Report</h1>
<div class="card"><div class="score">{result.risk_score}/100</div><p>{html.escape(result.summary)}</p></div>
<div class="card"><h2>Findings</h2><table><thead><tr><th>Severity</th><th>Category</th><th>Finding</th><th>Evidence</th><th>Remediation</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h2>Metrics</h2><pre>{payload}</pre></div>
</body></html>"""
    destination.write_text(document, encoding="utf-8")
    return destination
