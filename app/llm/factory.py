from typing import Optional
from app.llm.base import BaseLLM
from app.llm.ollama_llm import OllamaLLM
from app.llm.openai_llm import OpenAILLM
from app.llm.gemini_llm import GeminiLLM
from app.llm.deepseek_llm import DeepSeekLLM
from app.models.schemas import LLMProvider
from app.core.config import get_settings


class LLMFactory:
    """Factory class for creating LLM instances."""

    _providers = {
        LLMProvider.OLLAMA: OllamaLLM,
        LLMProvider.OPENAI: OpenAILLM,
        LLMProvider.GEMINI: GeminiLLM,
        LLMProvider.DEEPSEEK: DeepSeekLLM,
    }

    @classmethod
    def create(
        cls,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None
    ) -> BaseLLM:
        """
        Create an LLM instance based on the provider.

        Args:
            provider: The LLM provider to use. If None, uses default from settings.
            model: The specific model to use. If None, uses default for the provider.

        Returns:
            An instance of the requested LLM provider.
        """
        if provider is None:
            settings = get_settings()
            provider = LLMProvider(settings.default_llm_provider)

        llm_class = cls._providers.get(provider)
        if not llm_class:
            raise ValueError(f"Unknown LLM provider: {provider}")

        return llm_class(model=model)

    @classmethod
    def get_available_providers(cls) -> dict:
        """
        Get a dictionary of available providers and their status.

        Returns:
            Dict with provider names as keys and availability status as values.
        """
        status = {}
        for provider, llm_class in cls._providers.items():
            try:
                instance = llm_class()
                status[provider.value] = {
                    "available": instance.is_available(),
                    "model": instance.model_name
                }
            except Exception as e:
                status[provider.value] = {
                    "available": False,
                    "error": str(e)
                }
        return status
