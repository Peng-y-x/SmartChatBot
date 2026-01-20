from abc import ABC, abstractmethod
from collections.abc import Iterator

from typing import Awaitable, Callable

from chat_client_api.message import Message, Channel

__all__ = ["ChatClient", "get_client"]

class ChatClient(ABC):
    @abstractmethod
    def get_message(self, channel_id: str, message_id: str) -> Message:
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        raise NotImplementedError
    
    @abstractmethod
    def send_message(self, channel_id: str, content: str) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def get_channels(self) -> Iterator[Channel]:
        raise NotImplementedError

    @abstractmethod
    async def listen(self, on_message: Callable[[Message], Awaitable[None]]) -> None:
        """Listen for new messages and invoke callback with Message objects."""
        raise NotImplementedError
    
def get_client(client_data: dict[str, str]) -> ChatClient:
    raise NotImplementedError
