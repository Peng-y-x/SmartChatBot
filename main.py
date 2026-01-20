from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from typing import Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

import ai_client_api
import mail_client_api
import chat_client_api


logger = logging.getLogger(__name__)

app = FastAPI()


def _get_mail_client(user_id: str) -> mail_client_api.MailClient:
    return mail_client_api.get_mail_client(user_id=user_id)


def _parse_command_fallback(content: str) -> dict[str, Any] | None:
    text = content.strip().lower()
    if text in {"login", "login gmail", "link gmail"}:
        return {"action": "login"}
    if text in {"logout", "logout gmail", "unlink gmail"}:
        return {"action": "logout"}

    match = re.match(r"get\s+(\d+)\s+mail", text)
    if match:
        return {"action": "get_messages", "max_results": int(match.group(1))}

    match = re.match(r"get\s+mail\s+(\S+)", text)
    if match:
        return {"action": "get_message", "message_id": match.group(1)}

    match = re.match(r"delete\s+mail\s+(\S+)", text)
    if match:
        return {"action": "delete_message", "message_id": match.group(1)}

    match = re.match(r"read\s+mail\s+(\S+)", text)
    if match:
        return {"action": "mark_as_read", "message_id": match.group(1)}

    return None


def _parse_command_with_ai(content: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        ai_client = ai_client_api.get_ai_client()
    except Exception as exc:
        return None, f"AI client unavailable: {exc}"

    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "login",
                    "logout",
                    "get_messages",
                    "get_message",
                    "delete_message",
                    "mark_as_read",
                ],
            },
            "max_results": {"type": "integer"},
            "message_id": {"type": "string"},
        },
        "required": ["action"],
    }

    system_prompt = (
        "You are a Gmail assistant command parser. "
        "Return JSON only that matches the schema. No extra text. "
        "Map user intent to one of: login, logout, get_messages, get_message, "
        "delete_message, mark_as_read. "
        "If user asks for latest/recent/last emails, use get_messages. "
        "If user mentions a number, map to max_results (default 10 if omitted). "
        "If user provides an id, map to message_id."
    )
    try:
        result = ai_client.generate_response(
            content,
            system_prompt=system_prompt,
            response_schema=schema,
        )
    except Exception as exc:
        return None, f"AI parsing error: {exc}"
    if not isinstance(result, dict):
        return None, "AI response did not match expected JSON object"
    if "action" not in result:
        return None, "Parsed result missing required field: action"
    return result, None


def _fallback_ai_reply(content: str, reason: str | None) -> str | None:
    try:
        ai_client = ai_client_api.get_ai_client()
    except Exception:
        return None
    system_prompt = (
        "You are a helpful Gmail assistant in Discord DMs. "
        "Reply naturally and briefly. "
        "If the request is unclear, ask a short follow-up question. "
        "Do not mention internal schemas or tools."
    )
    if reason:
        system_prompt += f" Parsing failed because: {reason}"
    response = ai_client.generate_response(content, system_prompt=system_prompt)
    return response if isinstance(response, str) else None


def _parse_command(content: str) -> tuple[dict[str, Any] | None, str | None]:
    ai_result, reason = _parse_command_with_ai(content)
    if ai_result:
        return ai_result, None
    fallback = _parse_command_fallback(content)
    if fallback:
        return fallback, None
    return None, reason


def _format_messages(messages: list[mail_client_api.Message]) -> str:
    if not messages:
        return "No messages found."
    lines = []
    for msg in messages:
        lines.append(
            f"{msg.id} | {msg.date} | {msg.from_} | {msg.subject} | {msg.snippet}"
        )
    return "\n".join(lines)


def _clean_text(text: str) -> str:
    return html.unescape(text).strip()


def _format_message_entry(msg: mail_client_api.Message) -> str:
    subject = _clean_text(msg.subject)
    from_text = _clean_text(msg.from_)
    date_text = _clean_text(msg.date)
    snippet = _clean_text(msg.snippet)
    return (
        f"ID: {msg.id}\n"
        f"Subject: {subject}\n"
        f"From: {from_text}\n"
        f"Date: {date_text}\n"
        f"Snippet: {snippet}"
    )


def _split_message(text: str, limit: int = 1900) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        line_len = len(line) + 1
        if current and current_len + line_len > limit:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/mail/start")
def gmail_auth_start(discord_user_id: str) -> RedirectResponse:
    client = _get_mail_client(discord_user_id)
    data = client.login()
    return RedirectResponse(url=data["authorization_url"])


@app.get("/auth/mail/callback")
def gmail_auth_callback(code: str, state: str) -> HTMLResponse:
    client = _get_mail_client(user_id="")
    client.callback(code=code, state=state)
    return HTMLResponse("Mail authorized. You can return to Chat.")


def _make_chat_handler(chat_client: chat_client_api.ChatClient):
    async def _handle_chat_message(message: chat_client_api.Message) -> None:
        command, reason = _parse_command(message.content)
        if not command:
            reply = _fallback_ai_reply(message.content, reason)
            if reply:
                chat_client.send_message(message.channel_id, reply)
            return

        user_id = message.sender_id
        mail_client = _get_mail_client(user_id)

        try:
            action = command["action"]
            if action == "login":
                login_data = mail_client.login()
                chat_client.send_message(
                    message.channel_id,
                    f"Open this link to authorize Gmail:\n{login_data['authorization_url']}",
                )
                return
            if action == "logout":
                mail_client.logout()
                chat_client.send_message(message.channel_id, "Logged out from Gmail.")
                return
            if action == "get_messages":
                max_results = int(command.get("max_results") or 10)
                for msg in mail_client.get_messages(max_results=max_results):
                    entry = _format_message_entry(msg)
                    for chunk in _split_message(entry):
                        chat_client.send_message(message.channel_id, chunk)
                return
            if action == "get_message":
                msg_id = command.get("message_id")
                if not msg_id:
                    chat_client.send_message(message.channel_id, "Missing message id.")
                    return
                msg = mail_client.get_message(msg_id)
                body_text = f"{msg.subject}\nFrom: {msg.from_}\nTo: {msg.to}\n\n{msg.body}"
                for chunk in _split_message(body_text):
                    chat_client.send_message(message.channel_id, chunk)
                return
            if action == "delete_message":
                msg_id = command.get("message_id")
                if not msg_id:
                    chat_client.send_message(message.channel_id, "Missing message id.")
                    return
                mail_client.delete_message(msg_id)
                chat_client.send_message(message.channel_id, "Message deleted.")
                return
            if action == "mark_as_read":
                msg_id = command.get("message_id")
                if not msg_id:
                    chat_client.send_message(message.channel_id, "Missing message id.")
                    return
                mail_client.mark_as_read(msg_id)
                chat_client.send_message(message.channel_id, "Message marked as read.")
                return
        except Exception as exc:
            logger.exception("Command failed")
            if "No stored credentials for user" in str(exc):
                login_data = mail_client.login()
                chat_client.send_message(
                    message.channel_id,
                    "Please login to Gmail first:\n"
                    f"{login_data['authorization_url']}",
                )
                return
            chat_client.send_message(message.channel_id, f"Error: {exc}")

    return _handle_chat_message


async def _run_web() -> None:
    config = uvicorn.Config(
        app,
        host=os.environ.get("SMART_CHAT_BOT_HOST", "0.0.0.0"),
        port=int(os.environ.get("SMART_CHAT_BOT_PORT", "8000")),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def _run_bot() -> None:
    client = chat_client_api.get_client({})
    handler = _make_chat_handler(client)
    await client.listen(handler)


async def _main() -> None:
    await asyncio.gather(_run_web(), _run_bot())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
