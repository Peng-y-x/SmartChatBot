from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Iterator
from enum import IntEnum
from typing import Any, Awaitable, Callable

import discord
import httpx

import chat_client_api
from chat_client_api import ChatClient, Message, Channel

logger = logging.getLogger(__name__)


class HTTPStatus(IntEnum):
    """HTTP status codes used in Discord API responses."""

    NOT_FOUND = 404


class DiscordClient(ChatClient):
    DISCORD_API_BASE = "https://discord.com/api/v10"

    def __init__(self, client_data: dict[str, str] | None = None) -> None:
        self._client_data = client_data or {}
        self._token = self._client_data.get("bot_token") or os.environ.get("DISCORD_BOT_TOKEN")
        if not self._token:
            raise ValueError("DISCORD_BOT_TOKEN is required")

        self._http_client = httpx.Client(
            base_url=self.DISCORD_API_BASE,
            headers={"Authorization": f"Bot {self._token}"},
            timeout=30.0,
        )

        intents = discord.Intents.default()
        intents.message_content = True
        self._discord_client = _DiscordGatewayClient(intents=intents)

    async def listen(self, on_message: Callable[[Message], Awaitable[None]]) -> None:
        self._discord_client.set_message_handler(on_message)
        token = self._token
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        await self._discord_client.start(token)

    def get_message(self, channel_id: str, message_id: str) -> Message:
        try:
            response = self._http_client.get(
                f"/channels/{channel_id}/messages/{message_id}"
            )
            response.raise_for_status()
            return chat_client_api.get_message(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                raise ValueError(
                    f"Message {message_id} not found in channel {channel_id}"
                ) from exc
            raise ValueError(f"Failed to retrieve message: {exc}") from exc

    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        limit = min(limit, 100)
        try:
            response = self._http_client.get(
                f"/channels/{channel_id}/messages",
                params={"limit": limit},
            )
            response.raise_for_status()
            messages = response.json()
            return [chat_client_api.get_message(msg_data) for msg_data in messages]
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Failed to retrieve messages: {exc}") from exc

    def send_message(self, channel_id: str, content: str) -> bool:
        if not content.strip():
            raise ValueError("Message content cannot be empty")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return self._send_message_sync(channel_id, content)

        loop.create_task(asyncio.to_thread(self._send_message_sync, channel_id, content))
        return True

    def _send_message_sync(self, channel_id: str, content: str) -> bool:
        try:
            response = self._http_client.post(
                f"/channels/{channel_id}/messages",
                json={"content": content},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Failed to send message: {exc}") from exc

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        try:
            response = self._http_client.delete(
                f"/channels/{channel_id}/messages/{message_id}"
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                raise ValueError(
                    f"Message {message_id} not found in channel {channel_id}"
                ) from exc
            raise ValueError(f"Failed to delete message: {exc}") from exc

    def get_channels(self) -> Iterator[Channel]:
        for channel in self._discord_client.get_all_channels():
            yield chat_client_api.get_channel(
                {
                    "id": str(channel.id),
                    "name": getattr(channel, "name", ""),
                    "type": str(getattr(channel, "type", "0")),
                }
            )


class _DiscordGatewayClient(discord.Client):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._on_message: Callable[[Message], Awaitable[None]] | None = None

    def set_message_handler(self, handler: Callable[[Message], Awaitable[None]]) -> None:
        self._on_message = handler

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is not None:
            # Ignore messages from guild. Only reply to DM. 
            return
        if not self._on_message:
            return
        wrapped = chat_client_api.get_message(
            {
                "id": str(message.id),
                "channel_id": str(message.channel.id),
                "author": {
                    "id": str(message.author.id),
                    "username": message.author.name,
                    "global_name": getattr(message.author, "global_name", ""),
                },
                "content": message.content,
                "timestamp": str(message.created_at.isoformat()),
                "edited_timestamp": (
                    str(message.edited_at.isoformat()) if message.edited_at else ""
                ),
            }
        )
        await self._on_message(wrapped)
