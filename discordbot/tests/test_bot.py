"""Exercise the Discord command without loading models or calling an LLM."""

import importlib
import sys
import types
from unittest.mock import AsyncMock, Mock

import pytest

from config import Config


@pytest.fixture
def bot_module(monkeypatch):
    rag = types.ModuleType("RAG.GenResponce")
    rag.gen_response = Mock(return_value="回答")
    monkeypatch.setitem(sys.modules, "RAG.GenResponce", rag)
    monkeypatch.delitem(sys.modules, "bot", raising=False)
    module = importlib.import_module("bot")
    yield module
    sys.modules.pop("bot", None)


@pytest.mark.asyncio
@pytest.mark.parametrize("samples", [None, 0, 1, 3, 10])
async def test_handbook_passes_sample_count(bot_module, samples):
    client = bot_module.HandbookBot(Config("test-token", None))
    command = client.tree.get_command("handbook")
    interaction = Mock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    options = {} if samples is None else {"hyde_sample": samples}

    await command.callback(interaction, "  卒業条件  ", **options)

    bot_module.gen_response.assert_called_once_with(
        "卒業条件", hyde_sample=1 if samples is None else samples
    )
    interaction.response.defer.assert_awaited_once_with(thinking=True)
    interaction.followup.send.assert_awaited()


def test_sample_option_has_discord_bounds_and_default(bot_module):
    client = bot_module.HandbookBot(Config("test-token", None))
    command = client.tree.get_command("handbook")
    option = next(p for p in command.parameters if p.name == "hyde_sample")
    assert option.min_value == 0
    assert option.max_value == 10
    assert option.default == 1
    assert not option.required
