from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant/system)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    provider: Optional[LLMProvider] = Field(None, description="LLM provider to use")
    model: Optional[str] = Field(None, description="Specific model to use")
    use_rag: bool = Field(False, description="Whether to use RAG for context")
    conversation_history: List[ChatMessage] = Field(default_factory=list, description="Previous conversation messages")
    system_prompt: Optional[str] = Field(None, description="System prompt for the conversation")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    sources: Optional[List[str]] = Field(None, description="RAG sources if used")


class DocumentUploadResponse(BaseModel):
    filename: str = Field(..., description="Name of the uploaded file")
    status: str = Field(..., description="Upload status")
    chunks_created: int = Field(..., description="Number of text chunks created")
    message: str = Field(..., description="Status message")


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Query to search in documents")
    top_k: int = Field(5, description="Number of relevant chunks to retrieve")


class RAGQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]] = Field(..., description="List of relevant document chunks")


class HealthResponse(BaseModel):
    status: str
    providers: Dict[str, Any]


class ProviderModelsResponse(BaseModel):
    provider: str
    models: List[str]
    note: Optional[str] = None


class GenericResponse(BaseModel):
    status: str
    message: str
