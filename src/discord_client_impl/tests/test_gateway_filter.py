from typing import Any

import pytest
import discord

from discord_client_impl.discord_impl import _DiscordGatewayClient
from typing import cast


class _DummyAuthor:
    bot = False
    id = 1
    name = "user"
    global_name = None


class _DummyChannel:
    id = 123


class _DummyMessage:
    def __init__(self, *, guild: Any) -> None:
        self.author = _DummyAuthor()
        self.channel = _DummyChannel()
        self.guild = guild
        self.content = "hello"
        self.created_at = _DummyTime()
        self.edited_at = None


class _DummyTime:
    def isoformat(self) -> str:
        return "2025-01-01T00:00:00"


@pytest.mark.asyncio
async def test_gateway_ignores_guild_messages() -> None:
    client = _DiscordGatewayClient(intents=discord.Intents.default())
    called = False

    async def handler(_msg: Any) -> None:
        nonlocal called
        called = True

    client.set_message_handler(handler)
    await client.on_message(cast(discord.Message, _DummyMessage(guild="guild")))
    assert called is False
