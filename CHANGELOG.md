# Changelog

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
