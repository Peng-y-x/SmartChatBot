import time
from pathlib import Path

from gmail_client_impl.gmail_impl import GmailTokenStore


def test_token_store_consume_state(tmp_path: Path) -> None:
    store = GmailTokenStore(tmp_path / "tokens.sqlite")
    store.save_state("user1", "state123", ttl_seconds=60)
    user_id = store.consume_state("state123")
    assert user_id == "user1"
    assert store.consume_state("state123") is None


def test_token_store_state_expired(tmp_path: Path) -> None:
    store = GmailTokenStore(tmp_path / "tokens.sqlite")
    store.save_state("user1", "state123", ttl_seconds=1)
    time.sleep(2)
    assert store.consume_state("state123") is None
