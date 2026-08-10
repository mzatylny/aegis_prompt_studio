# Changelog

## 1.3.0

- add a versioned 41-case security benchmark with precision, recall, specificity, F1, category coverage, dataset hashing, and CI quality gates
- refine instruction-override and urgency-pressure rules with regression coverage
- add request correlation, privacy-safe structured JSON logs, and Prometheus-compatible HTTP metrics
- separate liveness and readiness checks and reject misconfigured live mode instead of silently falling back to demo behavior
- raise enforced test coverage from 75% to 90% and make CI permissions, concurrency, and timeouts explicit
- document the threat model, reliability targets, operational runbook, and major architecture decisions

## 1.2.0

- correct plain-keyword false positives in obfuscation detection
- inspect long decoded payloads without the previous 4,000-character cutoff
- reject oversized direct scanner input instead of silently truncating it
- validate final-report source IDs and apply requested recency policy
- add optional API-key protection and bounded research concurrency
- expand tests, CI coverage enforcement, and dependency auditing
- run containers as a non-root user with service health checks

## 1.1.0

- add bounded recursive decoding and expanded prompt-security regression coverage
- enforce post-retrieval source policy and citation-ledger integrity
