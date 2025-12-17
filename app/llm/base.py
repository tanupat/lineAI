from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator
from app.models.schemas import ChatMessage


class BaseLLM(ABC):
    """Base class for all LLM providers."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    @abstractmethod
    async def generate(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        message: str,
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available/configured."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self.model or "unknown"
