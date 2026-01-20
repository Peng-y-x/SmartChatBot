from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]

import mail_client_api
from .message_impl import GmailMessage

logger = logging.getLogger(__name__)

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEFAULT_STATE_TTL_SECONDS = 10 * 60
DEFAULT_TOKEN_DB = Path.home() / ".smart_chat_bot" / "gmail_tokens.sqlite"


class GmailTokenStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gmail_tokens (
                    user_id TEXT PRIMARY KEY,
                    credentials_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gmail_oauth_state (
                    user_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, state)
                )
                """
            )
            conn.commit()

    def save_credentials(self, user_id: str, credentials: Credentials) -> None:
        payload = credentials.to_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gmail_tokens (user_id, credentials_json)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET credentials_json = excluded.credentials_json
                """,
                (user_id, payload),
            )
            conn.commit()

    def load_credentials(self, user_id: str, scopes: list[str]) -> Credentials | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT credentials_json FROM gmail_tokens WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        info = json.loads(row[0])
        return Credentials.from_authorized_user_info(info, scopes=scopes)

    def delete_credentials(self, user_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM gmail_tokens WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
        return cursor.rowcount > 0

    def save_state(self, user_id: str, state: str, ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS) -> None:
        expires_at = int(time.time()) + ttl_seconds
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gmail_oauth_state (user_id, state, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, state) DO UPDATE SET expires_at = excluded.expires_at
                """,
                (user_id, state, expires_at),
            )
            conn.commit()

    def consume_state(self, state: str) -> str | None:
        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, expires_at FROM gmail_oauth_state WHERE state = ?",
                (state,),
            ).fetchone()
            if not row:
                return None
            user_id, expires_at = row
            conn.execute("DELETE FROM gmail_oauth_state WHERE state = ?", (state,))
            conn.execute("DELETE FROM gmail_oauth_state WHERE expires_at < ?", (now,))
            conn.commit()
        return user_id if expires_at >= now else None

    


class GmailClient(mail_client_api.MailClient):
    def __init__(
        self,
        *,
        user_id: str,
        credentials_path: str,
        redirect_uri: str,
        db_path: str | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        self.user_id = user_id
        self.credentials_path = credentials_path
        self.redirect_uri = redirect_uri
        self.scopes = scopes or list(DEFAULT_SCOPES)
        token_db = Path(db_path) if db_path else DEFAULT_TOKEN_DB
        self._token_store = GmailTokenStore(token_db)
        self._service = None

    def login(self) -> dict[str, str]:
        if not self.user_id:
            raise ValueError("user_id is required for login")

        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        self._token_store.save_state(self.user_id, state)
        return {"authorization_url": authorization_url, "state": state}

    def callback(self, code: str, state: str | None = None) -> dict[str, str]:
        if not state:
            raise ValueError("Missing OAuth state")
        
        user_id = self._token_store.consume_state(state)
        if not user_id:
            raise ValueError("Invalid or expired OAuth state")
        self.user_id = user_id

        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state,
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        self._token_store.save_credentials(self.user_id, credentials)
        return {"user_id": self.user_id}

    def logout(self) -> bool:
        self._service = None
        return self._token_store.delete_credentials(self.user_id)

    def _load_credentials(self) -> Credentials:
        credentials = self._token_store.load_credentials(self.user_id, self.scopes)
        if not credentials:
            raise ValueError("No stored credentials for user")

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self._token_store.save_credentials(self.user_id, credentials)
        return credentials

    def _get_service(self) -> Any:
        if not self._service:
            credentials = self._load_credentials()
            self._service = build("gmail", "v1", credentials=credentials)
        return self._service

    def get_message(self, message_id: str) -> mail_client_api.Message:
        service = self._get_service()
        msg_data = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return _parse_gmail_message(msg_data, include_body=True)

    def delete_message(self, message_id: str) -> bool:
        service = self._get_service()
        service.users().messages().delete(userId="me", id=message_id).execute()
        return True

    def mark_as_read(self, message_id: str) -> bool:
        service = self._get_service()
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True

    def get_messages(self, max_results: int = 10) -> Iterator[mail_client_api.Message]:
        service = self._get_service()
        response = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results)
            .execute()
        )
        for item in response.get("messages", []):
            msg_id = item.get("id")
            if not msg_id:
                continue
            msg_data = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Date", "Subject"],
                )
                .execute()
            )
            yield _parse_gmail_message(msg_data, include_body=False)


def _parse_gmail_message(data: dict[str, Any], *, include_body: bool) -> GmailMessage:
    payload = data.get("payload", {})
    headers = _extract_headers(payload)
    body = _extract_body(payload) if include_body else ""
    return GmailMessage(
        msg_id=data.get("id", ""),
        from_=headers.get("from", ""),
        to=headers.get("to", ""),
        date=headers.get("date", ""),
        subject=headers.get("subject", ""),
        snippet=data.get("snippet", ""),
        body=body,
    )


def _extract_headers(payload: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for header in payload.get("headers", []):
        name = header.get("name")
        value = header.get("value", "")
        if name:
            headers[name.lower()] = value
    return headers


def _extract_body(payload: dict[str, Any]) -> str:
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return _decode_body(body_data)

    for mime_type in ("text/plain", "text/html"):
        part_data = _find_part(payload, mime_type)
        if part_data:
            return _decode_body(part_data)
    return ""


def _find_part(payload: dict[str, Any], mime_type: str) -> str | None:
    for part in payload.get("parts", []):
        if part.get("mimeType") == mime_type and part.get("body", {}).get("data"):
            return part["body"]["data"]
        nested = _find_part(part, mime_type)
        if nested:
            return nested
    return None


def _decode_body(data: str) -> str:
    try:
        decoded = base64.urlsafe_b64decode(data.encode("utf-8"))
        return decoded.decode("utf-8", errors="replace")
    except Exception:
        logger.exception("Failed to decode message body")
        return ""


def get_client_impl(*, user_id: str) -> mail_client_api.MailClient:
    credentials_path = os.environ.get("GMAIL_CREDENTIALS_PATH")
    redirect_uri = os.environ.get("GMAIL_REDIRECT_URI")
    if not credentials_path or not redirect_uri:
        raise ValueError("GMAIL_CREDENTIALS_PATH and GMAIL_REDIRECT_URI must be set")
    db_path = os.environ.get("GMAIL_TOKEN_DB_PATH")
    return GmailClient(
        user_id=user_id,
        credentials_path=credentials_path,
        redirect_uri=redirect_uri,
        db_path=db_path,
    )


def register() -> None:
    mail_client_api.get_mail_client = get_client_impl
