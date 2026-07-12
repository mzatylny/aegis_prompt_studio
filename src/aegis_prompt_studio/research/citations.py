from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from aegis_prompt_studio.models import SourceRecord

TRUSTED_SUFFIXES = (
    ".gov",
    ".edu",
    ".ac.uk",
    "who.int",
    "oecd.org",
    "europa.eu",
    "un.org",
    "nature.com",
    "science.org",
    "springer.com",
    "ieee.org",
    "acm.org",
)


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def trust_score_for_domain(domain: str) -> float:
    domain = domain.lower()
    if any(domain.endswith(suffix) for suffix in TRUSTED_SUFFIXES):
        return 0.92
    if domain.endswith(".org"):
        return 0.72
    if domain.endswith(".com"):
        return 0.58
    return 0.5


def _walk(value: object) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)


def extract_sources(response: object, limit: int = 30) -> list[SourceRecord]:
    """Extract citation and web-search source metadata from an OpenAI response object."""
    if hasattr(response, "model_dump"):
        payload = response.model_dump(mode="json")
    elif isinstance(response, dict):
        payload = response
    else:
        payload = {}

    by_url: dict[str, SourceRecord] = {}
    for node in _walk(payload):
        url = node.get("url") or node.get("source_website_url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        title = node.get("title") or node.get("name") or domain_from_url(url) or "Web source"
        snippet = node.get("snippet") or node.get("text") or node.get("description") or ""
        domain = domain_from_url(url)
        if url not in by_url:
            by_url[url] = SourceRecord(
                title=str(title)[:300],
                url=url,
                domain=domain,
                snippet=str(snippet)[:700],
                trust_score=trust_score_for_domain(domain),
            )
        if len(by_url) >= limit:
            break
    return list(by_url.values())
