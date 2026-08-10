# Security policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Do not disclose suspected vulnerabilities in a public issue. Use the repository's **Security** tab to submit a private vulnerability report. If private reporting is unavailable, contact the maintainer through their GitHub profile before sharing technical details.

Include the affected component, reproduction steps, impact, and any suggested mitigation. Please remove credentials, private data, and active exploit payloads that could harm third parties.

## Scope

Useful reports include prompt-scanner bypasses, unsafe output handling, source-policy bypasses, authentication or authorization failures, secret exposure, and dependency vulnerabilities with a demonstrated impact on this project.

The current trust boundaries, residual risks, and out-of-scope controls are documented in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md). Scanner changes should include adversarial and benign-neighbor cases as described in [docs/SECURITY_EVALUATION.md](docs/SECURITY_EVALUATION.md).
