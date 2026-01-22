from abc import ABC, abstractmethod
from collections.abc import Iterator

from .message import Message

class MailClient(ABC):
    @abstractmethod
    def login(self) -> dict[str, str]:
        """Start provider-specific login or authorization flow.

        Implementations can return an authorization URL, token data, or
        provider-specific metadata needed to complete the flow.
        """
        raise NotImplementedError
    
    @abstractmethod
    def callback(self, code: str, state: str | None = None) -> dict[str, str]:
        """Handle provider callback step to finalize authorization."""
        raise NotImplementedError

    @abstractmethod
    def logout(self) -> bool:
        """Remove stored credentials for the current user."""
        raise NotImplementedError
    
    @abstractmethod
    def get_message(self, message_id: str) -> Message:
        """Return a full message including the body."""
        raise NotImplementedError
    
    @abstractmethod
    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID."""
        raise NotImplementedError
    
    @abstractmethod
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read by ID."""
        raise NotImplementedError
    
    @abstractmethod
    def get_messages(self, max_results: int=10) -> Iterator[Message]:
        """Return a list of recent messages.

        Implementations may return summaries only. In that case, Message.body
        can be empty or partial and callers should use get_message() for full
        content.
        """
        raise NotImplementedError
    
def get_mail_client(*, user_id: str) -> MailClient:
    raise NotImplementedError
