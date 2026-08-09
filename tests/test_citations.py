from datetime import UTC, datetime

from aegis_prompt_studio.models import SourceRecord
from aegis_prompt_studio.research.citations import (
    canonical_public_url,
    domain_from_url,
    filter_sources,
    parse_publication_date,
    trust_score_for_domain,
)


def source(url: str) -> SourceRecord:
    return SourceRecord(title=url, url=url, domain=domain_from_url(url))


def test_trusted_domain_matching_resists_suffix_spoofing() -> None:
    assert trust_score_for_domain("who.int") == 0.92
    assert trust_score_for_domain("data.who.int") == 0.92
    assert trust_score_for_domain("evilwho.int") == 0.5


def test_domain_parser_uses_hostname_not_credentials_or_port() -> None:
    assert domain_from_url("https://user:pass@WWW.Example.GOV.:443/report") == "example.gov"


def test_canonical_url_rejects_local_and_credentialed_targets() -> None:
    assert canonical_public_url("http://127.0.0.1/private") is None
    assert canonical_public_url("https://user:pass@example.com/") is None
    assert canonical_public_url("https://Example.com:443/report#section") == (
        "https://example.com/report"
    )


def test_source_policy_is_enforced_after_retrieval() -> None:
    sources = [
        source("https://docs.example.org/guide"),
        source("https://blocked.example.org/page"),
        source("https://example.org.evil.test/spoof"),
    ]
    filtered = filter_sources(
        sources,
        allowed_domains=["example.org"],
        blocked_domains=["blocked.example.org"],
    )
    assert [item.domain for item in filtered] == ["docs.example.org"]


def test_publication_dates_are_parsed_and_old_sources_are_filtered() -> None:
    recent = source("https://example.gov/recent")
    recent.published_at = parse_publication_date("2026-07-01")
    old = source("https://example.gov/old")
    old.published_at = parse_publication_date("2020-01-01")
    filtered = filter_sources(
        [old, recent],
        recent_after=datetime(2024, 8, 9, tzinfo=UTC),
    )
    assert [item.title for item in filtered] == [recent.title]
    assert recent.published_at == datetime(2026, 7, 1, tzinfo=UTC)
