from typing import List, Optional, AsyncGenerator
import google.generativeai as genai
from app.llm.base import BaseLLM
from app.models.schemas import ChatMessage
from app.core.config import get_settings


class GeminiLLM(BaseLLM):
    """Google Gemini LLM provider."""

    def __init__(self, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = settings.google_api_key
        self.model = model or settings.gemini_model

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
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
            raise ValueError("Google API key not configured")

        # Build conversation content
        contents = self._build_contents(message, conversation_history, system_prompt)

        response = await self.client.generate_content_async(
            contents,
            generation_config=genai.types.GenerationConfig(
                **kwargs
            ) if kwargs else None
        )
        return response.text

    async def generate_stream(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            raise ValueError("Google API key not configured")

        contents = self._build_contents(message, conversation_history, system_prompt)

        response = await self.client.generate_content_async(
            contents,
            generation_config=genai.types.GenerationConfig(
                **kwargs
            ) if kwargs else None,
            stream=True
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def _build_contents(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None
    ) -> List[dict]:
        contents = []

        # Add system prompt as first user message if provided
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [f"System instruction: {system_prompt}"]
            })
            contents.append({
                "role": "model",
                "parts": ["Understood. I will follow these instructions."]
            })

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = "model" if msg.role == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [msg.content]
                })

        # Add current message
        contents.append({
            "role": "user",
            "parts": [message]
        })

        return contents

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"
