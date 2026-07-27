"""Tests for the asynchronous RAG API client."""

from collections.abc import Callable

import httpx
import pytest

from rag_client import (
    RagClient,
    RagConnectionError,
    RagResponseError,
    RagTimeoutError,
)


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> RagClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return RagClient("http://rag.test/query", http_client=http_client)


@pytest.mark.asyncio
async def test_successful_response_and_request_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("http://rag.test/query")
        assert request.headers["content-type"] == "application/json"
        assert request.content == b'{"question":"question"}'
        return httpx.Response(
            200,
            json={
                "answer": "回答",
                "sources": [{"document": "学生便覧", "page": 42}],
            },
        )

    client = make_client(handler)
    try:
        response = await client.query("question")
    finally:
        await client.aclose()

    assert response.answer == "回答"
    assert len(response.sources) == 1
    assert response.sources[0].document == "学生便覧"
    assert response.sources[0].page == 42


@pytest.mark.asyncio
async def test_successful_response_without_sources() -> None:
    client = make_client(
        lambda request: httpx.Response(
            200,
            json={"answer": "確認できませんでした。", "sources": []},
        )
    )
    try:
        response = await client.query("question")
    finally:
        await client.aclose()

    assert response.sources == []


@pytest.mark.asyncio
async def test_http_500_is_response_error() -> None:
    client = make_client(lambda request: httpx.Response(500, text="secret detail"))
    try:
        with pytest.raises(RagResponseError):
            await client.query("question")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_non_json_response_is_response_error() -> None:
    client = make_client(lambda request: httpx.Response(200, text="not json"))
    try:
        with pytest.raises(RagResponseError):
            await client.query("question")
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"sources": []},
        {"answer": "", "sources": []},
        {"answer": "   ", "sources": []},
        {"answer": "回答", "sources": {}},
        {"answer": "回答", "sources": [{"document": "便覧", "page": 0}]},
        {"answer": "回答", "sources": [{"document": "便覧", "page": True}]},
        {"answer": "回答", "sources": [{"document": 123, "page": 1}]},
    ],
)
async def test_invalid_payload_is_response_error(payload: object) -> None:
    client = make_client(lambda request: httpx.Response(200, json=payload))
    try:
        with pytest.raises(RagResponseError):
            await client.query("question")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_connection_error_is_converted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = make_client(handler)
    try:
        with pytest.raises(RagConnectionError):
            await client.query("question")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_timeout_is_converted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = make_client(handler)
    try:
        with pytest.raises(RagTimeoutError):
            await client.query("question")
    finally:
        await client.aclose()
