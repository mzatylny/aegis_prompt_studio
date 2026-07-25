# Architecture

## Overview

Aegis Prompt Studio contains two independent application services behind a shared set of typed models:

- `security`: deterministic prompt-risk analysis and defensive transformations
- `research`: orchestrated research workflow with demonstration and live providers

Both services are available through Streamlit, FastAPI, and the command line.

## Security analysis flow

```text
Raw input
  → length boundary
  → HTML and Unicode normalization
  → invisible character removal
  → encoded payload extraction
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

FastAPI response models validate every public response.

## Extension points

- add new security rules to `security/scanner.py`
- add decoders to `security/normalization.py`
- replace `OpenAIResearchProvider` with another provider implementing the same stage methods
- persist traces and results in a database
- add authentication and per-user quotas at the API layer
- connect a vector store for internal document research

