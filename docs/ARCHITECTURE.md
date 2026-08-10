# Architecture

## Overview

Aegis Prompt Studio contains two independent application services behind a shared set of typed models:

- `security`: deterministic prompt-risk analysis and defensive transformations
- `research`: orchestrated research workflow with demonstration and live providers

Both services are available through Streamlit, FastAPI, and the command line.

Cross-cutting deterministic controls and observability sit at the API and pipeline boundaries. Model stages cannot override input limits, source policy, claim validation, or final citation validation.

## Security analysis flow

```text
Raw input
  → length boundary
  → HTML and Unicode normalization
  → invisible character removal
  → encoded payload extraction
  → explicit rejection above the configured input boundary
  → rule engine over original, normalized, and decoded forms
  → finding deduplication
  → saturating risk aggregation
  → defensive wrapper and controls
```

The risk score uses a saturating aggregation rather than a simple sum. Independent findings increase risk, while repeated instances of the same pattern do not create unlimited score inflation.

## Research workflow

```text
Untrusted topic
  → local security gate
  → planner
  → web researcher
  → adversarial critic
  → structured fact-checker
  → report writer
  → claim ledger, source list, trace, and quality score
  → deterministic final-report citation validation
```

### Planner

Produces a typed `ResearchPlan` containing subquestions, searches, evaluation criteria, and risk notes.

### Researcher

In live mode, uses the OpenAI Responses API hosted `web_search` tool. Retrieved content is explicitly described as untrusted evidence. Domain filters can be supplied by the user.

### Critic

Searches the evidence dossier for unsupported claims, weak source selection, outdated evidence, causal overreach, and missing counterarguments.

### Fact-checker

Returns a typed claim ledger. Every claim has a support status, confidence score, source identifiers, and notes.

### Writer

Uses only the evidence dossier, critic review, verified claim ledger, and source index. The final report separates facts, inferences, counterarguments, and limitations.

## Runtime modes

### Demo

- no external requests
- deterministic plan and trace
- illustrative source records
- suitable for interface review and automated testing

### Live

- requires `OPENAI_API_KEY`
- structured planner and fact-checker outputs
- current web search
- source metadata extraction
- multi-stage model calls

## API boundaries

- `POST /v1/security/scan`
- `POST /v1/security/mutate`
- `POST /v1/research/run`
- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

FastAPI response models validate every public response.

When `AEGIS_API_KEY` is configured, every POST endpoint requires a matching `X-API-Key` header. Research execution is bounded by `MAX_CONCURRENT_RESEARCH`; excess requests fail quickly with a retry hint rather than creating an unbounded queue.

The request middleware generates or validates a correlation ID, records process-local metrics using route templates, and emits structured metadata-only JSON logs. It never reads the request body. Live configuration is checked before research admission so a missing provider key cannot downgrade current research to deterministic demo data.

## Evaluation boundary

```text
Versioned JSON corpus
  → schema and unique-ID validation
  → deterministic scanner execution
  → confusion matrix and category coverage
  → precision, recall, specificity, accuracy, and F1
  → CI policy decision
```

The dataset SHA-256 is included in each machine-readable report. The gate protects known behavior from regression; it does not convert curated results into a production accuracy claim.

## Operational model

- liveness tests process responsiveness;
- readiness verifies required configuration for the selected mode;
- request metrics use method, route template, and status labels;
- JSON logs use a bounded correlation ID and omit bodies, headers, and raw URLs;
- research concurrency and all text/decoder inputs are explicitly bounded.

See [OPERATIONS.md](OPERATIONS.md), [THREAT_MODEL.md](THREAT_MODEL.md), and the decision records in `docs/decisions/`.

## Extension points

- add new security rules to `security/scanner.py`
- add decoders to `security/normalization.py`
- replace `OpenAIResearchProvider` with another provider implementing the same stage methods
- persist traces and results in a database
- add authentication and per-user quotas at the API layer
- replace process-local metrics and concurrency limits with shared platform services
- connect a vector store for internal document research
