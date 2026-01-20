from fastapi.testclient import TestClient

import main


class _DummyMailClient:
    def login(self) -> dict[str, str]:
        return {"authorization_url": "http://auth.local/login", "state": "state"}

    def callback(self, code: str, state: str | None = None) -> dict[str, str]:
        return {"user_id": "user1"}


def test_health_route() -> None:
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_start_redirect(monkeypatch) -> None:
    client = TestClient(main.app)
    monkeypatch.setattr(main, "_get_mail_client", lambda *_args, **_kwargs: _DummyMailClient())
    response = client.get(
        "/auth/mail/start",
        params={"discord_user_id": "user1"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 307}
    assert response.headers["location"] == "http://auth.local/login"


def test_auth_callback_returns_html(monkeypatch) -> None:
    client = TestClient(main.app)
    monkeypatch.setattr(main, "_get_mail_client", lambda *_args, **_kwargs: _DummyMailClient())
    response = client.get("/auth/mail/callback", params={"code": "abc", "state": "state"})
    assert response.status_code == 200
    assert "Mail authorized" in response.text
