import httpx
from typing import List, Optional, AsyncGenerator
from app.llm.base import BaseLLM
from app.models.schemas import ChatMessage
from app.core.config import get_settings


class OllamaLLM(BaseLLM):
    """Ollama LLM provider for local models."""

    def __init__(self, model: Optional[str] = None):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model = model or settings.ollama_model

    async def generate(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        messages = self._build_messages(message, conversation_history, system_prompt)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def generate_stream(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(message, conversation_history, system_prompt)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content

    def _build_messages(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None
    ) -> List[dict]:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": message})
        return messages

    def is_available(self) -> bool:
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "ollama"
