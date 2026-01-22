from abc import ABC, abstractmethod
from typing import Any

class Message(ABC):

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def channel_id(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def sender_id(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def sender_name(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def content(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def timestamp(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def edited_timestamp(self) -> str | None:
        raise NotImplementedError
    
class Channel(ABC):
    @property
    @abstractmethod
    def channel_id(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def channel_type(self) -> str:
        raise NotImplementedError
    
def get_message(raw_data: dict[str, Any]) -> Message:
    '''
    Return an instance of a chat message.
    
    Args:
        raw_data: Dictionary containing raw message data from the chat platform.

    Returns:
        Message: An instance conforming to the Message contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    '''
    raise NotImplementedError

def get_channel(raw_data: dict[str, Any]) -> Channel:
    """Return an instance of a Channel.

    Args:
        raw_data: Dictionary containing raw channel data from the chat platform.

    Returns:
        Channel: An instance conforming to the Channel contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
