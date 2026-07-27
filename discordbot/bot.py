"""Discord entry point for the student-handbook RAG bot."""

from __future__ import annotations

import logging
import sys

import discord
from discord import app_commands

from config import Config, ConfigError, load_config
from formatter import format_response, split_message
from rag_client import (
    RagClient,
    RagConnectionError,
    RagResponseError,
    RagTimeoutError,
)

logger = logging.getLogger(__name__)

INVALID_QUESTION_MESSAGE = "質問は1文字以上500文字以内で入力してください。"
CONNECTION_ERROR_MESSAGE = (
    "RAGサーバーに接続できませんでした。サーバーの起動状態を確認してください。"
)
TIMEOUT_ERROR_MESSAGE = (
    "回答生成がタイムアウトしました。しばらくしてから再度実行してください。"
)
RESPONSE_ERROR_MESSAGE = "RAGサーバーから不正な応答が返されました。"
UNEXPECTED_ERROR_MESSAGE = "処理中に予期しないエラーが発生しました。"


class HandbookBot(discord.Client):
    """Discord client exposing the /handbook slash command."""

    def __init__(self, config: Config) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self._guild_id = config.discord_guild_id
        self._rag_client = RagClient(config.rag_api_url)
        self._register_commands()

    def _register_commands(self) -> None:
        @self.tree.command(
            name="handbook",
            description="学生便覧について質問します",
        )
        @app_commands.describe(question="学生便覧について知りたいこと")
        async def handbook(
            interaction: discord.Interaction,
            question: str,
        ) -> None:
            normalized_question = question.strip()
            if not normalized_question or len(normalized_question) > 500:
                await interaction.response.send_message(
                    INVALID_QUESTION_MESSAGE,
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return

            await interaction.response.defer(thinking=True)
            try:
                response = await self._rag_client.query(normalized_question)
                message = format_response(response.answer, response.sources)
                for chunk in split_message(message):
                    await interaction.followup.send(
                        chunk,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
            except RagConnectionError:
                logger.warning("Command failed because the RAG API was unreachable")
                await self._send_error(interaction, CONNECTION_ERROR_MESSAGE)
            except RagTimeoutError:
                logger.warning("Command failed because the RAG API timed out")
                await self._send_error(interaction, TIMEOUT_ERROR_MESSAGE)
            except RagResponseError:
                logger.warning("Command failed because the RAG response was invalid")
                await self._send_error(interaction, RESPONSE_ERROR_MESSAGE)
            except Exception:
                logger.exception("Unexpected error while processing /handbook")
                await self._send_error(interaction, UNEXPECTED_ERROR_MESSAGE)

    async def _send_error(
        self,
        interaction: discord.Interaction,
        message: str,
    ) -> None:
        await interaction.followup.send(
            message,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def setup_hook(self) -> None:
        """Synchronize commands once during initial Discord setup."""
        if self._guild_id is not None:
            guild = discord.Object(id=self._guild_id)
            self.tree.copy_global_to(guild=guild)
            commands = await self.tree.sync(guild=guild)
            logger.info(
                "Command sync completed: scope=guild guild_id=%d commands=%d",
                self._guild_id,
                len(commands),
            )
        else:
            commands = await self.tree.sync()
            logger.info(
                "Command sync completed: scope=global commands=%d",
                len(commands),
            )

    async def on_ready(self) -> None:
        """Log successful Discord authentication without exposing credentials."""
        logger.info("Discord login succeeded: user=%s user_id=%s", self.user, self.user.id)

    async def close(self) -> None:
        """Close both Discord and the reusable RAG HTTP client."""
        logger.info("Bot is shutting down")
        await self._rag_client.aclose()
        await super().close()


def main() -> None:
    """Load configuration and run the Discord bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    logger.info("Bot is starting")
    bot = HandbookBot(config)
    bot.run(config.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
