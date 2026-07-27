"""Discord entry point for the student-handbook RAG bot."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import discord
from discord import app_commands
from openai import APIConnectionError, APITimeoutError

from config import Config, ConfigError, load_config
from formatter import format_response, split_message

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from RAG.GenResponce import gen_response

logger = logging.getLogger(__name__)

INVALID_QUESTION_MESSAGE = "質問は1文字以上500文字以内で入力してください。"
CONNECTION_ERROR_MESSAGE = (
    "RAGサーバーに接続できませんでした。サーバーの起動状態を確認してください。"
)
TIMEOUT_ERROR_MESSAGE = (
    "回答生成がタイムアウトしました。しばらくしてから再度実行してください。"
)
UNEXPECTED_ERROR_MESSAGE = "処理中に予期しないエラーが発生しました。"
RESPONSE_TIMEOUT_SECONDS = 120


class HandbookBot(discord.Client):
    """Discord client exposing the /handbook slash command."""

    def __init__(self, config: Config) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self._guild_id = config.discord_guild_id
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
                answer = await asyncio.wait_for(
                    asyncio.to_thread(gen_response, normalized_question),
                    timeout=RESPONSE_TIMEOUT_SECONDS,
                )
                message = format_response(answer, [])
                for chunk in split_message(message):
                    await interaction.followup.send(
                        chunk,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
            except APIConnectionError:
                logger.warning("Command failed because vLLM was unreachable")
                await self._send_error(interaction, CONNECTION_ERROR_MESSAGE)
            except (TimeoutError, APITimeoutError):
                logger.warning("Command failed because response generation timed out")
                await self._send_error(interaction, TIMEOUT_ERROR_MESSAGE)
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
