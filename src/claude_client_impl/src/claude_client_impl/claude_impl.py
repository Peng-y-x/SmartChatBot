from typing import Any
import json
import anthropic
from dotenv import load_dotenv
import os

import ai_client_api

load_dotenv()

claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class ClaudeClient(ai_client_api.AIClient):

    def generate_response(
        self,
        user_input: str,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,        
    )  -> str | dict[str, Any] :
        directives: list[str] = []
        if system_prompt:
            directives.append(system_prompt.strip())

        if response_schema is not None:
            directives.append(
                "You must return JSON that strictly conforms to the following schema:\n"
                f"{json.dumps(response_schema)}\n"
                "Do not include any extra text—only valid JSON."
            )

        system_text = "\n\n".join(directives) if directives else None

        messages = [{"role": "user", "content": user_input}]

        request_kwargs: dict[str, Any] = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1024,
            "messages": messages,
        }
        if system_text is not None:
            request_kwargs["system"] = system_text

        api_response = claude_client.messages.create(**request_kwargs)

        content = api_response.content[0].text.strip()
        if response_schema is None:
            return content

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            invalid_json_message = "Claude returned invalid JSON for the provided schema"
            raise ValueError(invalid_json_message) from exc
        if not isinstance(parsed, dict):
            invalid_json_message = "Claude returned data that does not match the expected schema"
            raise TypeError(invalid_json_message)
        return parsed
    
