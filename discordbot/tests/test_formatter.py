"""Tests for Discord response formatting and splitting."""

from formatter import DISCORD_MESSAGE_LIMIT, format_response, split_message
from rag_client import Source


def test_formats_one_source() -> None:
    result = format_response(
        "卒業には167単位以上必要です。",
        [Source(document="2026年度学生便覧", page=42)],
    )

    assert result == (
        "卒業には167単位以上必要です。\n\n"
        "**出典**\n- 2026年度学生便覧 p.42"
    )


def test_formats_multiple_sources_in_order() -> None:
    result = format_response(
        "回答",
        [
            Source(document="学生便覧", page=42),
            Source(document="履修要項", page=7),
        ],
    )

    assert result == (
        "回答\n\n**出典**\n"
        "- 学生便覧 p.42\n"
        "- 履修要項 p.7"
    )


def test_omits_source_heading_when_sources_are_empty() -> None:
    assert format_response("確認できませんでした。", []) == "確認できませんでした。"


def test_removes_duplicate_sources_while_preserving_order() -> None:
    result = format_response(
        "回答",
        [
            Source(document="学生便覧", page=42),
            Source(document="学生便覧", page=43),
            Source(document="学生便覧", page=42),
        ],
    )

    assert result.count("- 学生便覧 p.42") == 1
    assert result.index("p.42") < result.index("p.43")


def test_does_not_split_message_at_or_below_limit() -> None:
    text = "あ" * DISCORD_MESSAGE_LIMIT
    assert split_message(text) == [text]


def test_all_long_message_chunks_are_within_limit() -> None:
    text = ("段落です。" * 500) + "\n\n" + ("次の段落です。" * 500)
    chunks = split_message(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= DISCORD_MESSAGE_LIMIT for chunk in chunks)


def test_splitting_does_not_lose_content() -> None:
    text = ("あいうえお。\n" * 700) + "@everyone"
    assert "".join(split_message(text)) == text


def test_mentions_are_neutralized_in_answer_and_source() -> None:
    result = format_response(
        "@everyone <@123> @here",
        [Source(document="@everyone便覧", page=1)],
    )

    assert "@everyone" not in result
    assert "@here" not in result
    assert "<@123>" not in result
