import base64

from gmail_client_impl.gmail_impl import _decode_body, _extract_headers


def test_extract_headers_lowercases_keys() -> None:
    payload = {
        "headers": [
            {"name": "From", "value": "Alice <a@example.com>"},
            {"name": "Subject", "value": "Hi"},
        ]
    }
    headers = _extract_headers(payload)
    assert headers["from"] == "Alice <a@example.com>"
    assert headers["subject"] == "Hi"


def test_decode_body_base64url() -> None:
    raw = "Hello world"
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    assert _decode_body(encoded) == raw
