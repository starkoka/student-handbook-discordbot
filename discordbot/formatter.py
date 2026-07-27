"""Format and split RAG answers for safe display in Discord."""

from __future__ import annotations

from collections.abc import Iterable

from rag_client import Source

DISCORD_MESSAGE_LIMIT = 1900
_SPLIT_DELIMITERS = ("\n\n", "\n", "。")


def format_response(answer: str, sources: Iterable[Source]) -> str:
    """Combine an answer and its unique citations into Discord Markdown."""
    safe_answer = escape_mentions(answer)
    unique_sources = _unique_sources(sources)
    if not unique_sources:
        return safe_answer

    source_lines = [
        f"- {escape_mentions(source.document)} p.{source.page}"
        for source in unique_sources
    ]
    return f"{safe_answer}\n\n**出典**\n" + "\n".join(source_lines)


def escape_mentions(text: str) -> str:
    """Neutralize common Discord mention forms in untrusted API text."""
    return (
        text.replace("@everyone", "@\u200beveryone")
        .replace("@here", "@\u200bhere")
        .replace("<@", "<@\u200b")
    )


def split_message(
    text: str,
    limit: int = DISCORD_MESSAGE_LIMIT,
) -> list[str]:
    """Split text without loss, preferring paragraph and sentence boundaries."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not text:
        return [""]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        split_at = _preferred_split_position(window)
        if split_at == 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


def _unique_sources(sources: Iterable[Source]) -> list[Source]:
    unique: list[Source] = []
    seen: set[tuple[str, int]] = set()
    for source in sources:
        key = (source.document, source.page)
        if key not in seen:
            seen.add(key)
            unique.append(source)
    return unique


def _preferred_split_position(window: str) -> int:
    for delimiter in _SPLIT_DELIMITERS:
        index = window.rfind(delimiter)
        if index >= 0:
            return index + len(delimiter)
    return 0
