import base64

from gmail_client_impl.gmail_impl import _extract_body, _find_part


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


def test_extract_body_prefers_plain() -> None:
    payload = {
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<b>Hi</b>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("Hi")}},
        ]
    }
    assert _extract_body(payload) == "Hi"


def test_find_part_nested() -> None:
    payload = {
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Nested")}}
                ],
            }
        ]
    }
    assert _find_part(payload, "text/plain") is not None
