# ADR 0002: Privacy-safe, low-cardinality observability

- Status: accepted
- Date: 2026-08-11

## Context

Operators need enough telemetry to diagnose latency, saturation, failures, and configuration problems. Prompts, research topics, headers, and source URLs may contain confidential data or attacker-controlled values. Recording them also creates unbounded metric labels and a second sensitive data store.

## Decision

Log only bounded request metadata and use framework route templates for metrics. Correlate requests with a validated or generated ID. Expose process-local Prometheus text metrics without request bodies, headers, user identifiers, prompt text, or source URLs.

## Consequences

- Operators can measure availability, latency, status distribution, and in-flight work.
- Logs remain useful for correlation while reducing data-exposure risk.
- Content-specific debugging requires a deliberate, consented reproduction rather than retrospective prompt inspection.
- Multi-process aggregation, durable storage, alerting, access control, and retention remain deployment responsibilities.
