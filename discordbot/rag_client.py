"""Asynchronous client for the external student-handbook RAG API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import (
    CONNECT_TIMEOUT_SECONDS,
    POOL_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
    WRITE_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    """A document and page cited by a RAG response."""

    document: str
    page: int


@dataclass(frozen=True)
class RagResponse:
    """A validated answer returned by the RAG API."""

    answer: str
    sources: list[Source]


class RagClientError(Exception):
    """Base class for failures while querying the RAG API."""


class RagConnectionError(RagClientError):
    """Raised when the RAG API cannot be reached."""


class RagTimeoutError(RagClientError):
    """Raised when a RAG API operation times out."""


class RagResponseError(RagClientError):
    """Raised when the RAG API returns an invalid response."""


class RagClient:
    """Reusable asynchronous HTTP client for the RAG API."""

    def __init__(
        self,
        api_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        timeout = httpx.Timeout(
            connect=CONNECT_TIMEOUT_SECONDS,
            read=READ_TIMEOUT_SECONDS,
            write=WRITE_TIMEOUT_SECONDS,
            pool=POOL_TIMEOUT_SECONDS,
        )
        self._api_url = api_url
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self._closed = False

    async def query(self, question: str) -> RagResponse:
        """Send a question and return a validated RAG response."""
        started_at = time.perf_counter()
        logger.info("RAG request started: question_length=%d", len(question))
        try:
            response = await self._http_client.post(
                self._api_url,
                json={"question": question},
            )
        except httpx.TimeoutException as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000)
            logger.warning("RAG request timed out: elapsed_ms=%d", elapsed_ms)
            raise RagTimeoutError("RAG API request timed out") from exc
        except httpx.RequestError as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000)
            logger.warning(
                "RAG connection failed: elapsed_ms=%d error_type=%s",
                elapsed_ms,
                type(exc).__name__,
            )
            raise RagConnectionError("Could not connect to the RAG API") from exc

        if response.status_code != httpx.codes.OK:
            logger.warning("RAG response returned HTTP %d", response.status_code)
            raise RagResponseError(
                f"RAG API returned HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("RAG response was not valid JSON")
            raise RagResponseError("RAG API response was not valid JSON") from exc

        rag_response = _validate_response(data)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        logger.info(
            "RAG request completed: elapsed_ms=%d sources=%d",
            elapsed_ms,
            len(rag_response.sources),
        )
        return rag_response

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        if not self._closed:
            await self._http_client.aclose()
            self._closed = True


def _validate_response(data: Any) -> RagResponse:
    if not isinstance(data, dict):
        raise RagResponseError("RAG API response must be a JSON object")

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise RagResponseError("RAG API response has an invalid answer")

    sources_data = data.get("sources")
    if not isinstance(sources_data, list):
        raise RagResponseError("RAG API response has invalid sources")

    sources: list[Source] = []
    for item in sources_data:
        if not isinstance(item, dict):
            raise RagResponseError("RAG API response has an invalid source")
        document = item.get("document")
        page = item.get("page")
        if not isinstance(document, str):
            raise RagResponseError("RAG API source has an invalid document")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise RagResponseError("RAG API source has an invalid page")
        sources.append(Source(document=document, page=page))

    return RagResponse(answer=answer, sources=sources)
