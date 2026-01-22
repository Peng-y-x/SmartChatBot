import ai_client_api
from .claude_impl import ClaudeClient

def get_ai_client_impl() -> ai_client_api.AIClient:
    """Return a ClaudeAIInterface instance."""
    return ClaudeClient()


def register() -> None:
    """Register the Claude AI interface factory with ai_chat_api."""
    ai_client_api.get_ai_client = get_ai_client_impl

register()