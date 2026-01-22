import chat_client_api
from .discord_impl import DiscordClient
from .message_impl import DiscordMessage, DiscordChannel

def get_client_impl(client_data: dict[str, str] | None = None) -> chat_client_api.ChatClient:
    return DiscordClient(client_data)

def get_message_impl(raw_data: dict[str, str]) -> chat_client_api.Message:
    return DiscordMessage(raw_data)

def get_channel_impl(raw_data: dict[str, str]) -> chat_client_api.Channel:
    return DiscordChannel(raw_data)

def register() -> None:
    chat_client_api.get_client = get_client_impl
    chat_client_api.get_message = get_message_impl
    chat_client_api.get_channel = get_channel_impl

register()
