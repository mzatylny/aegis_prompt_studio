from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import TextIO
from uuid import uuid4

REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def resolve_request_id(value: str | None) -> str:
    """Preserve a safe caller request ID or create a correlation ID."""
    if value and REQUEST_ID.fullmatch(value):
        return value
    return uuid4().hex


class JsonLogFormatter(logging.Formatter):
    """Emit operational fields as JSON without serializing request bodies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_json_logger(
    name: str,
    level: str = "INFO",
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure an isolated JSON logger once and leave root logging untouched."""
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    logger.propagate = False
    if not any(getattr(handler, "_aegis_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(JsonLogFormatter())
        handler._aegis_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger


@dataclass
class RequestAggregate:
    count: int = 0
    duration_seconds: float = 0.0


class ApiMetrics:
    """Thread-safe, low-cardinality HTTP metrics in Prometheus text format."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._in_flight = 0
        self._requests: dict[tuple[str, str, int], RequestAggregate] = defaultdict(
            RequestAggregate
        )

    def start_request(self) -> None:
        with self._lock:
            self._in_flight += 1

    def finish_request(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        key = (method.upper(), route, status_code)
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            aggregate = self._requests[key]
            aggregate.count += 1
            aggregate.duration_seconds += max(0.0, duration_seconds)

    def render_prometheus(self) -> str:
        with self._lock:
            in_flight = self._in_flight
            snapshot = [
                (key, RequestAggregate(value.count, value.duration_seconds))
                for key, value in self._requests.items()
            ]

        lines = [
            "# HELP aegis_http_requests_in_flight Current HTTP requests.",
            "# TYPE aegis_http_requests_in_flight gauge",
            f"aegis_http_requests_in_flight {in_flight}",
            "# HELP aegis_http_requests_total Completed HTTP requests.",
            "# TYPE aegis_http_requests_total counter",
            "# HELP aegis_http_request_duration_seconds Request duration in seconds.",
            "# TYPE aegis_http_request_duration_seconds summary",
        ]
        for (method, route, status_code), aggregate in sorted(snapshot):
            labels = (
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",'
                f'status="{status_code}"'
            )
            lines.append(f"aegis_http_requests_total{{{labels}}} {aggregate.count}")
            lines.append(
                "aegis_http_request_duration_seconds_sum"
                f"{{{labels}}} {aggregate.duration_seconds:.9f}"
            )
            lines.append(
                f"aegis_http_request_duration_seconds_count{{{labels}}} {aggregate.count}"
            )
        return "\n".join(lines) + "\n"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
