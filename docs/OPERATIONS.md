# Operations and reliability

## Service objectives

These are initial engineering targets for a production deployment, not measurements from the demo environment:

| Signal | Target | Measurement |
|---|---:|---|
| API availability | 99.9% monthly | non-5xx responses, excluding approved maintenance |
| Local scan latency | p95 below 250 ms for inputs up to 50,000 characters | HTTP duration metrics |
| Research admission | reject over-capacity work within 100 ms | `429` latency and count |
| Citation integrity | 100% known source IDs in returned live reports | deterministic report validator |
| Security regression | precision, recall, and F1 at least 90% | versioned CI benchmark |

Provider latency and availability are tracked separately because live research depends on external model and search services.

## Health endpoints

- `GET /health/live` confirms the process can answer requests.
- `GET /health/ready` confirms the selected mode has required configuration.
- `GET /health` is the compatibility summary used by local tooling.

Orchestrators should use liveness only to restart a stuck process and readiness to decide whether traffic can be sent. In live mode, a missing `OPENAI_API_KEY` returns `503` from readiness and research execution.

## Metrics

`GET /metrics` returns Prometheus-compatible, process-local HTTP metrics:

- `aegis_http_requests_in_flight`
- `aegis_http_requests_total{method,route,status}`
- `aegis_http_request_duration_seconds_{sum,count}{method,route,status}`

Routes use framework templates, not raw URLs, to bound label cardinality. The endpoint contains no prompt text, request headers, or credentials. Restrict it to the monitoring network in a shared deployment.

## Logs and privacy

Request logs are structured JSON with timestamp, level, event, request ID, method, route template, status, and duration. `X-Request-ID` is preserved only when it matches a bounded safe format; otherwise the service generates one.

The middleware does not read request bodies. Do not add prompt text, research content, API-key headers, full source URLs, or model request payloads to operational logs. Central log storage should enforce retention, encryption, and access controls.

## Capacity and failure behavior

- Scanner and mutation work is bounded by `MAX_INPUT_CHARS`.
- At most `MAX_CONCURRENT_RESEARCH` research calls run per process.
- Excess research requests return `429` with `Retry-After: 5`.
- Provider or pipeline failures return `502` with details kept in server logs.
- Research concurrency is process-local; multi-replica deployments need a gateway or distributed quota service for global limits.

## OpenAI transport and TLS

OpenAI Python SDK 3.x uses HTTPX2 internally. The application constructs the default SDK client;
do not inject a legacy `httpx.Client` into it. If a custom proxy, transport, timeout object, event
hook, or request mock is required, use `httpx2` and the SDK's `DefaultHttpx2Client` helpers.

HTTPX2 verifies TLS certificates against the operating-system trust store. Deployments behind a
TLS-inspecting proxy or private certificate authority must install the required CA certificate in
that trust store or configure `SSL_CERT_FILE`/`SSL_CERT_DIR`. Validate this with a live staging
request from the same container image used in production. A deployment configured with a
`socks5://` or `socks5h://` proxy must also install the HTTPX2 SOCKS dependency (`socksio`).

## Incident checklist

1. Confirm readiness, error rate, latency, and in-flight work.
2. Correlate the failing request with `X-Request-ID`; do not request the user's secret or raw credential.
3. Determine whether the failure is local validation, saturation, configuration, or provider dependency.
4. For suspected source-integrity failures, preserve the run metadata and source IDs without publishing sensitive content.
5. Rotate affected credentials and disable live research if a key may be exposed.
6. Add a minimized regression case, document the root cause, and rerun the quality and security gates before restoration.
