from typing import Any

import pytest

from discord_client_impl.discord_impl import DiscordClient
import httpx


class _DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ValueError("http error")

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyHttpClient:
    def __init__(self) -> None:
        self.last_request: tuple[str, str, dict[str, Any]] | None = None

    def post(self, url: str, json: dict[str, Any]) -> _DummyResponse:
        self.last_request = ("post", url, json)
        return _DummyResponse()


class _ErrorHttpClient:
    def __init__(self, status_code: int) -> None:
        self._status_code = status_code

    def get(self, url: str, params: dict[str, Any] | None = None) -> _DummyResponse:
        request = httpx.Request("GET", f"https://discord.com{url}")
        response = httpx.Response(self._status_code, request=request)
        raise httpx.HTTPStatusError("error", request=request, response=response)

    def delete(self, url: str) -> _DummyResponse:
        request = httpx.Request("DELETE", f"https://discord.com{url}")
        response = httpx.Response(self._status_code, request=request)
        raise httpx.HTTPStatusError("error", request=request, response=response)


def test_send_message_sync_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    client = DiscordClient({})
    dummy = _DummyHttpClient()
    client._http_client = dummy  # type: ignore[assignment]

    assert client.send_message("123", "hello") is True
    assert dummy.last_request == ("post", "/channels/123/messages", {"content": "hello"})


def test_send_message_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    client = DiscordClient({})
    with pytest.raises(ValueError):
        client.send_message("123", "  ")


def test_get_message_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    client = DiscordClient({})
    client._http_client = _ErrorHttpClient(404)  # type: ignore[assignment]
    with pytest.raises(ValueError):
        client.get_message("123", "456")


def test_delete_message_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token")
    client = DiscordClient({})
    client._http_client = _ErrorHttpClient(404)  # type: ignore[assignment]
    with pytest.raises(ValueError):
        client.delete_message("123", "456")
