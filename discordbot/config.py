"""Environment-based configuration for the Discord bot."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 120.0
WRITE_TIMEOUT_SECONDS = 10.0
POOL_TIMEOUT_SECONDS = 5.0


class ConfigError(ValueError):
    """Raised when an environment variable is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Validated runtime configuration."""

    discord_bot_token: str
    rag_api_url: str
    discord_guild_id: int | None


def load_config() -> Config:
    """Load and validate configuration from the environment and a .env file."""
    load_dotenv()

    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    rag_api_url = os.getenv("RAG_API_URL", "").strip()
    missing = [
        name
        for name, value in (
            ("DISCORD_BOT_TOKEN", discord_bot_token),
            ("RAG_API_URL", rag_api_url),
        )
        if not value
    ]
    if missing:
        names = ", ".join(missing)
        raise ConfigError(f"必須の環境変数が設定されていません: {names}")

    guild_id_text = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id: int | None = None
    if guild_id_text:
        try:
            guild_id = int(guild_id_text)
        except ValueError as exc:
            raise ConfigError(
                "DISCORD_GUILD_IDには正の整数を指定してください。"
            ) from exc
        if guild_id <= 0:
            raise ConfigError("DISCORD_GUILD_IDには正の整数を指定してください。")

    return Config(
        discord_bot_token=discord_bot_token,
        rag_api_url=rag_api_url,
        discord_guild_id=guild_id,
    )
