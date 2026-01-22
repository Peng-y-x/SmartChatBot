import mail_client_api

class GmailMessage(mail_client_api.Message):

    def __init__(
            self,
            *,
            msg_id: str,
            from_: str,
            to: str,
            date: str,
            subject: str,
            snippet: str,
            body: str,
    ) -> None:
        self._msg_id = msg_id
        self._from_ = from_
        self._to = to
        self._date = date
        self._subject = subject
        self._snippet = snippet
        self._body = body

    @property
    def id(self) -> str:
        return self._msg_id

    @property
    def from_(self) -> str:
        return self._from_

    @property
    def to(self) -> str:
        return self._to

    @property
    def date(self) -> str:
        return self._date

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def snippet(self) -> str:
        return self._snippet

    @property
    def body(self) -> str:
        return self._body

'''
{
  "id": "1789...",
  "snippet": "Hello ...",
  "payload": {
    "mimeType": "multipart/alternative",
    "headers": [
      {"name": "From", "value": "Alice <alice@example.com>"},
      {"name": "To", "value": "Bob <bob@example.com>"},
      {"name": "Subject", "value": "Hi"},
      {"name": "Date", "value": "Mon, 1 Jan 2025 10:00:00 +0000"}
    ],
    "parts": [
      {"mimeType": "text/plain", "body": {"data": "base64..." }},
      {"mimeType": "text/html", "body": {"data": "base64..." }}
    ]
  }
}
'''