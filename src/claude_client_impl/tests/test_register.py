import ai_client_api
import claude_client_impl


def test_register_sets_factory() -> None:
    claude_client_impl.register()
    client = ai_client_api.get_ai_client()
    assert client is not None
