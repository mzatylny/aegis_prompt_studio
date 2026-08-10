# ADR 0001: Deterministic checks remain the security boundary

- Status: accepted
- Date: 2026-08-11

## Context

A model can recognize contextual attacks that a rule engine misses, but using the same class of model as the only guard introduces nondeterminism, latency, cost, and susceptibility to the content being evaluated. The project needs a testable boundary for input limits, source policy, citation identifiers, and known injection patterns.

## Decision

Keep deterministic normalization, bounded decoding, rule matching, URL validation, claim-ledger validation, and final citation validation as mandatory controls. Model-based planning, critique, fact-checking, and writing operate behind those controls and cannot waive them.

Scanner behavior is measured against a versioned corpus. A model-based classifier may be added later as an advisory signal, but it must fail closed or degrade explicitly and must not replace deterministic authorization or output validation.

## Consequences

- Security regressions can block CI with reproducible evidence.
- Local scanning remains fast, inspectable, and available without a provider key.
- Novel semantic attacks can evade deterministic patterns, so red-team expansion and defense in depth remain necessary.
- Rule changes must balance recall with benign near-neighbor cases to prevent silent false-positive growth.
