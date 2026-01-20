from abc import ABC, abstractmethod
from typing import Any

class AIClient(ABC):
    
    @abstractmethod
    def generate_response(
        self,
        user_input: str,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:

        raise NotImplementedError
    
def get_ai_client() -> AIClient:
    raise NotImplementedError

