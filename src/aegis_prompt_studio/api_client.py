"""Browser-session research requests use the API's shared execution controls."""

from __future__ import annotations

import httpx

from aegis_prompt_studio.models import ResearchQuestion, ResearchResult


class ResearchRequestError(RuntimeError):
    """A safe, user-facing error from the research service."""


def request_research(
    question: ResearchQuestion, *, base_url: str, access_key: str = ""
) -> ResearchResult:
    headers = {"X-API-Key": access_key} if access_key else {}
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/v1/research/run",
            json=question.model_dump(mode="json"),
            headers=headers,
            timeout=600.0,
        )
    except httpx.RequestError as exc:
        raise ResearchRequestError("The research service is unavailable. Please try again.") from exc
    if response.status_code != 200:
        messages = {
            401: "Enter a valid access key to run research.",
            429: "Research capacity is full. Please try again shortly.",
            503: "The research service is not ready. Contact the operator.",
        }
        raise ResearchRequestError(
            messages.get(response.status_code, "The research request could not be completed.")
        )
    try:
        return ResearchResult.model_validate(response.json())
    except ValueError as exc:
        raise ResearchRequestError("The research service returned an invalid result.") from exc
