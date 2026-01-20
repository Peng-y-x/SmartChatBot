import os

from fastapi.testclient import TestClient

import main
import mail_client_api


def test_e2e_health_smoke() -> None:
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200


def test_e2e_gmail_get_messages() -> None:
    user_id = os.environ.get("E2E_USER_ID", "e2e-user")
    mail_client = mail_client_api.get_mail_client(user_id=user_id)
    messages = list(mail_client.get_messages(max_results=1))
    assert messages is not None
