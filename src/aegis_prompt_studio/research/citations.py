from __future__ import annotations

from collections.abc import Iterable
from ipaddress import ip_address
from urllib.parse import urlparse, urlunparse

from aegis_prompt_studio.models import SourceRecord

TRUSTED_SUFFIXES = (
    ".gov",
    ".edu",
    ".ac.uk",
    "gov.uk",
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


def normalize_domain(domain: str) -> str:
    """Return a canonical ASCII hostname suitable for policy comparisons."""
    domain = domain.strip().lower().rstrip(".")
    if not domain:
        return ""
    try:
        return domain.encode("idna").decode("ascii")
    except UnicodeError:
        return ""


def domain_from_url(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    domain = normalize_domain(hostname)
    return domain.removeprefix("www.")


def domain_matches(domain: str, policy_domain: str) -> bool:
    """Match an exact hostname or its subdomains without suffix-spoofing."""
    domain = normalize_domain(domain).removeprefix("www.")
    policy_domain = normalize_domain(policy_domain).removeprefix("www.")
    return bool(policy_domain) and (
        domain == policy_domain or domain.endswith(f".{policy_domain}")
    )


def _matches_trusted_suffix(domain: str, suffix: str) -> bool:
    if suffix.startswith("."):
        return domain.endswith(suffix) and len(domain) > len(suffix)
    return domain_matches(domain, suffix)


def trust_score_for_domain(domain: str) -> float:
    domain = normalize_domain(domain).removeprefix("www.")
    if any(_matches_trusted_suffix(domain, suffix) for suffix in TRUSTED_SUFFIXES):
        return 0.92
    if domain.endswith(".org"):
        return 0.72
    if domain.endswith(".com"):
        return 0.58
    return 0.5


def canonical_public_url(url: str) -> str | None:
    """Validate and canonicalize a public HTTP(S) citation URL."""
    try:
        parsed = urlparse(url.strip())
        hostname = normalize_domain(parsed.hostname or "")
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    if parsed.username or parsed.password:
        return None
    try:
        address = ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        return None
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return None

    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    display_host = f"[{hostname}]" if address and address.version == 6 else hostname
    netloc = display_host if port is None or default_port else f"{display_host}:{port}"
    return urlunparse(
        (parsed.scheme.lower(), netloc, parsed.path or "/", parsed.params, parsed.query, "")
    )


def filter_sources(
    sources: Iterable[SourceRecord],
    *,
    allowed_domains: Iterable[str] = (),
    blocked_domains: Iterable[str] = (),
    limit: int = 30,
) -> list[SourceRecord]:
    """Enforce domain policy again after retrieval and deduplicate canonical URLs."""
    allowed = [normalize_domain(item) for item in allowed_domains if normalize_domain(item)]
    blocked = [normalize_domain(item) for item in blocked_domains if normalize_domain(item)]
    selected: list[SourceRecord] = []
    seen: set[str] = set()

    for source in sources:
        canonical = canonical_public_url(str(source.url))
        if canonical is None or canonical in seen:
            continue
        domain = domain_from_url(canonical)
        if any(domain_matches(domain, item) for item in blocked):
            continue
        if allowed and not any(domain_matches(domain, item) for item in allowed):
            continue
        seen.add(canonical)
        selected.append(
            source.model_copy(
                update={
                    "url": canonical,
                    "domain": domain,
                    "trust_score": trust_score_for_domain(domain),
                }
            )
        )
        if len(selected) >= max(0, limit):
            break
    return selected


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
        if not isinstance(url, str):
            continue
        canonical = canonical_public_url(url)
        if canonical is None:
            continue
        title = node.get("title") or node.get("name") or domain_from_url(canonical) or "Web source"
        snippet = node.get("snippet") or node.get("text") or node.get("description") or ""
        domain = domain_from_url(canonical)
        if canonical not in by_url:
            by_url[canonical] = SourceRecord(
                title=str(title)[:300],
                url=canonical,
                domain=domain,
                snippet=str(snippet)[:700],
                trust_score=trust_score_for_domain(domain),
            )
        if len(by_url) >= limit:
            break
    return list(by_url.values())
