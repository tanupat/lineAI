from typing import List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.llm.base import BaseLLM
from app.models.schemas import ChatMessage
from app.core.config import get_settings


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM provider (uses OpenAI-compatible API)."""

    def __init__(self, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = model or settings.deepseek_model

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None

    async def generate(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        if not self.client:
            raise ValueError("DeepSeek API key not configured")

        messages = self._build_messages(message, conversation_history, system_prompt)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    async def generate_stream(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            raise ValueError("DeepSeek API key not configured")

        messages = self._build_messages(message, conversation_history, system_prompt)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
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
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "deepseek"
