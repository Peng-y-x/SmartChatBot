from typing import cast

import pytest

import main
import chat_client_api


class _DummyMessage:
    def __init__(self, content: str, sender_id: str = "user1", channel_id: str = "chan1") -> None:
        self.content = content
        self.sender_id = sender_id
        self.channel_id = channel_id


class _DummyChatClient:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_message(self, channel_id: str, content: str) -> bool:
        self.sent.append((channel_id, content))
        return True


class _DummyMailClient:
    def __init__(self, *, raise_on_get: bool = False) -> None:
        self.raise_on_get = raise_on_get

    def login(self) -> dict[str, str]:
        return {"authorization_url": "http://auth.local/login", "state": "state"}

    def logout(self) -> bool:
        return True

    def get_messages(self, max_results: int = 10):
        if self.raise_on_get:
            raise ValueError("No stored credentials for user")
        return []

    def get_message(self, message_id: str):
        class _Msg:
            id = message_id
            subject = "Subj"
            from_ = "from@example.com"
            to = "to@example.com"
            body = "Body"

        return _Msg()

    def delete_message(self, message_id: str) -> bool:
        return True

    def mark_as_read(self, message_id: str) -> bool:
        return True


def test_parse_command_fallback_get_messages() -> None:
    result = main._parse_command_fallback("get 5 mail")
    assert result == {"action": "get_messages", "max_results": 5}


def test_split_message_chunks() -> None:
    text = "\n".join(["x" * 1000, "y" * 1000, "z" * 1000])
    chunks = main._split_message(text, limit=1900)
    assert len(chunks) == 3
    assert "x" in chunks[0]
    assert "z" in chunks[2]


@pytest.mark.asyncio
async def test_handler_login_sends_link(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "login"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient())

    await handler(_DummyMessage("login"))
    assert chat_client.sent
    assert "http://auth.local/login" in chat_client.sent[0][1]


@pytest.mark.asyncio
async def test_handler_logout(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "logout"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient())

    await handler(_DummyMessage("logout"))
    assert chat_client.sent
    assert "Logged out" in chat_client.sent[0][1]


@pytest.mark.asyncio
async def test_handler_not_logged_in_sends_login_link(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "get_messages"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient(raise_on_get=True))

    await handler(_DummyMessage("get 1 mail"))
    assert chat_client.sent
    assert "Please login to Gmail first" in chat_client.sent[0][1]


@pytest.mark.asyncio
async def test_handler_get_message_missing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "get_message"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient())

    await handler(_DummyMessage("get mail"))
    assert chat_client.sent
    assert "Missing message id" in chat_client.sent[0][1]


@pytest.mark.asyncio
async def test_handler_mark_as_read_missing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "mark_as_read"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient())

    await handler(_DummyMessage("read mail"))
    assert chat_client.sent
    assert "Missing message id" in chat_client.sent[0][1]


@pytest.mark.asyncio
async def test_handler_delete_missing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_client = _DummyChatClient()
    handler = main._make_chat_handler(cast(chat_client_api.ChatClient, chat_client))

    monkeypatch.setattr(main, "_parse_command", lambda _content: ({"action": "delete_message"}, None))
    monkeypatch.setattr(main, "_get_mail_client", lambda _user_id: _DummyMailClient())

    await handler(_DummyMessage("delete mail"))
    assert chat_client.sent
    assert "Missing message id" in chat_client.sent[0][1]


def test_fallback_ai_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyAI:
        def generate_response(self, _content: str, **kwargs: object) -> str:
            system_prompt = str(kwargs.get("system_prompt", ""))
            if "Parsing failed because: reason" in system_prompt:
                return "failed: reason"
            return "hello"

    monkeypatch.setattr(main.ai_client_api, "get_ai_client", lambda: _DummyAI())
    assert main._fallback_ai_reply("hi", None) == "hello"


def test_fallback_ai_reply_includes_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyAI:
        def generate_response(self, _content: str, **kwargs: object) -> str:
            system_prompt = str(kwargs.get("system_prompt", ""))
            return "ok" if "Parsing failed because: bad" in system_prompt else "nope"

    monkeypatch.setattr(main.ai_client_api, "get_ai_client", lambda: _DummyAI())
    assert main._fallback_ai_reply("hi", "bad") == "ok"


def test_parse_command_ai_failure_fallback() -> None:
    command, reason = main._parse_command("get 2 mail")
    assert command == {"action": "get_messages", "max_results": 2}
    assert reason is None
