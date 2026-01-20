from gmail_client_impl.message_impl import GmailMessage


def test_gmail_message_properties() -> None:
    msg = GmailMessage(
        msg_id="abc123",
        from_="from@example.com",
        to="to@example.com",
        date="2025-01-01",
        subject="Hello",
        snippet="Preview text",
        body="Body text",
    )

    assert msg.id == "abc123"
    assert msg.from_ == "from@example.com"
    assert msg.to == "to@example.com"
    assert msg.date == "2025-01-01"
    assert msg.subject == "Hello"
    assert msg.snippet == "Preview text"
    assert msg.body == "Body text"
