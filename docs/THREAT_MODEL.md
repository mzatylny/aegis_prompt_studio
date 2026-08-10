# Threat model

## Scope and assets

Aegis accepts untrusted prompt text and research topics, optionally retrieves public web content, calls a model provider, and returns findings or a sourced report. Assets that require protection are:

- application and provider credentials;
- trusted application instructions and tool policy;
- user-supplied content and generated reports;
- source and claim integrity;
- service availability and audit evidence.

The browser-facing Streamlit app, public API, retrieved web content, model provider, and operator environment are separate trust zones. User text and retrieved content remain untrusted across every boundary.

## Primary threats and controls

| Threat | Example impact | Current controls | Residual risk |
|---|---|---|---|
| Direct prompt injection | policy override or hidden-prompt extraction | original/normalized/decoded scanning, hardened data boundary, least-privilege guidance | novel phrasing and contextual attacks can evade rules |
| Indirect injection | retrieved page controls an agent | untrusted-content instructions, post-retrieval URL policy, source index separation | a model can still be influenced by malicious evidence text |
| Secret disclosure | API key or environment value exposed | secrets kept outside prompts, API responses omit configuration, logs exclude bodies and headers | operator misconfiguration or third-party provider retention |
| SSRF/source-policy bypass | access to local or credential-bearing URLs | canonical URL validation, private/local address rejection, post-retrieval allow/block enforcement | DNS rebinding and provider-side retrieval behavior are outside this process |
| Citation fabrication | unsupported claims appear grounded | typed claim ledger, source-ID validation before writing, final-report citation validation | a valid citation may still not support the exact claim |
| Resource exhaustion | oversized input or expensive concurrent research | input limits, bounded decoding, research semaphore, fast `429` response | no distributed per-identity quota in the reference service |
| Unauthorized API use | unapproved scans or paid research | constant-time optional API-key check | shared keys lack user identity and fine-grained authorization |
| Observability leakage | prompts or secrets copied to logs | request metadata only, route templates instead of raw URLs, no bodies/headers | exception text from dependencies still requires operator review |
| Configuration downgrade | expected live research silently becomes demo output | readiness failure and explicit rejection when live credentials are missing | incorrect model or origin configuration can still reduce quality |

## Abuse cases

- A user embeds encoded override instructions in a document submitted for analysis.
- A retrieved page tells the research agent to ignore the source policy or invent citations.
- An attacker submits many deep research requests to exhaust provider budget.
- A caller supplies high-cardinality paths or identifiers to overload metrics storage.
- An operator deploys live mode without a provider credential and assumes results are current.

## Security invariants

1. No request body, API key, or model credential is written to application request logs.
2. Live mode never silently falls back to demo mode.
3. Unknown source IDs never reach the report as verified citations.
4. User and retrieved content never gain instruction authority by placement alone.
5. Scanner and decoder work remains bounded by explicit size and depth limits.

## Out of scope

The reference service does not provide enterprise identity, tenant isolation, distributed rate limiting, TLS termination, a durable audit store, malware analysis, or a guarantee that model output is safe. Production deployments should provide these controls at the platform boundary.
