import json
from io import StringIO

from aegis_prompt_studio.observability import ApiMetrics, configure_json_logger, resolve_request_id


def test_request_id_validation() -> None:
    assert resolve_request_id("safe-request_123") == "safe-request_123"
    assert resolve_request_id("unsafe request") != "unsafe request"
    assert len(resolve_request_id(None)) == 32


def test_metrics_use_bounded_route_labels() -> None:
    metrics = ApiMetrics()
    metrics.start_request()
    metrics.finish_request("get", "/v1/items/{item_id}", 200, 0.125)
    rendered = metrics.render_prometheus()
    assert 'method="GET",route="/v1/items/{item_id}",status="200"' in rendered
    assert "aegis_http_requests_total" in rendered
    assert " 1\n" in rendered
    assert "0.125000000" in rendered


def test_json_logger_contains_operational_fields_without_payloads() -> None:
    stream = StringIO()
    logger = configure_json_logger("aegis-test-json-logger", stream=stream)
    logger.info(
        "http_request_completed",
        extra={
            "request_id": "req-1",
            "method": "POST",
            "route": "/v1/security/scan",
            "status_code": 200,
            "duration_ms": 2.5,
        },
    )
    payload = json.loads(stream.getvalue())
    assert payload["request_id"] == "req-1"
    assert payload["route"] == "/v1/security/scan"
    assert "body" not in payload
    assert "api_key" not in payload
