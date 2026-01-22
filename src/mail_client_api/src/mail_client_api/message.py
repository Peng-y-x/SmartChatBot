from abc import ABC, abstractmethod

class Message(ABC):
    """Abstract base class representing an email message."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def from_(self) -> str:
        """Return the sender's email address."""
        raise NotImplementedError

    @property
    @abstractmethod
    def to(self) -> str:
        """Return the recipient's email address."""
        raise NotImplementedError

    @property
    @abstractmethod
    def date(self) -> str:
        """Return the date the message was sent."""
        raise NotImplementedError

    @property
    @abstractmethod
    def subject(self) -> str:
        """Return the subject line of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def snippet(self) -> str:
        """Return a short preview of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def body(self) -> str:
        """Return the plain text content of the message.

        When returned from get_messages(), implementations may leave this empty
        or partial if only a summary is available.
        """
        raise NotImplementedError
