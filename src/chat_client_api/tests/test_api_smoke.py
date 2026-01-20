import chat_client_api


def test_get_client_callable() -> None:
    try:
        client = chat_client_api.get_client({})
    except NotImplementedError:
        return
    assert client is not None
