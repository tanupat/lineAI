from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # LINE
    line_channel_secret: str = ""
    line_channel_access_token: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Google Gemini
    google_api_key: str = ""
    gemini_model: str = "gemini-pro"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Default LLM Provider
    default_llm_provider: str = "ollama"

    # RAG
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "/tmp/chroma_db"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Upload
    upload_dir: str = "/tmp/uploads/documents"
    max_file_size: int = 10485760  # 10MB

    # Database
    database_type: str = "sqlite"  # sqlite or postgresql
    database_url: str = "sqlite+aiosqlite:///./line_ai.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
