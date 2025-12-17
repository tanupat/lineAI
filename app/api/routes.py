import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Header, status
from fastapi.responses import StreamingResponse
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentUploadResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    HealthResponse,
    LLMProvider,
    ProviderModelsResponse,
    GenericResponse
)
from app.llm.factory import LLMFactory
from app.rag.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy initialization for services
_rag_service: Optional[RAGService] = None
_line_handler = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_line_handler():
    global _line_handler
    if _line_handler is None:
        from app.line.line_handler import LineHandler
        _line_handler = LineHandler()
    return _line_handler


# ============== Health Check ==============

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API Health",
    description="Check the health of the API and the status of configured LLM providers."
)
async def health_check():
    providers = LLMFactory.get_available_providers()
    line_handler = get_line_handler()
    providers["line"] = {"available": line_handler.is_available()}

    return HealthResponse(
        status="healthy",
        providers=providers
    )


# ============== Chat Endpoints ==============

@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Chat with LLM",
    description="Send a message to the configured LLM provider. Supports RAG if enabled."
)
async def chat(request: ChatRequest):
    """
    Send a chat message and get a response.
    
    - **message**: The user's input message
    - **provider**: (Optional) Specific LLM provider to use
    - **model**: (Optional) Specific model
    - **use_rag**: (Optional) Enable RAG context injection
    """
    try:
        rag_service = get_rag_service()

        # Get RAG context if enabled
        context = ""
        sources = []
        if request.use_rag:
            context, sources = await rag_service.get_context_for_query(request.message)

        # Build system prompt
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        if context:
            system_prompt += f"\n\nRelevant context from documents:\n{context}"

        # Create LLM and generate response
        llm = LLMFactory.create(request.provider, request.model)

        response = await llm.generate(
            message=request.message,
            conversation_history=request.conversation_history,
            system_prompt=system_prompt
        )

        return ChatResponse(
            response=response,
            provider=llm.provider_name,
            model=llm.model_name,
            sources=sources if sources else None
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat/stream",
    tags=["Chat"],
    summary="Stream Chat Response",
    description="Stream the response from the LLM token by token. Useful for real-time UI updates."
)
async def chat_stream(request: ChatRequest):
    """
    Send a chat message and get a streaming response (Server-Sent Events).
    """
    try:
        rag_service = get_rag_service()

        # Get RAG context if enabled
        context = ""
        if request.use_rag:
            context, _ = await rag_service.get_context_for_query(request.message)

        # Build system prompt
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        if context:
            system_prompt += f"\n\nRelevant context from documents:\n{context}"

        # Create LLM
        llm = LLMFactory.create(request.provider, request.model)

        async def generate():
            async for chunk in llm.generate_stream(
                message=request.message,
                conversation_history=request.conversation_history,
                system_prompt=system_prompt
            ):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== RAG Endpoints ==============

@router.post(
    "/rag/upload",
    response_model=DocumentUploadResponse,
    tags=["RAG"],
    summary="Upload Document for RAG",
    description="Upload a document (PDF, TXT, etc.) to be indexed for Retrieval-Augmented Generation."
)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for RAG.
    
    Supported formats: .txt, .pdf, .docx, .md, .json, .csv
    """
    try:
        rag_service = get_rag_service()
        filename, chunks = await rag_service.upload_document(file)

        return DocumentUploadResponse(
            filename=filename,
            status="success",
            chunks_created=chunks,
            message=f"Document '{filename}' processed and {chunks} chunks created."
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    tags=["RAG"],
    summary="Query RAG Documents",
    description="Search through uploaded documents for relevant context chunks."
)
async def query_documents(request: RAGQueryRequest):
    try:
        rag_service = get_rag_service()
        results = await rag_service.query(request.query, request.top_k)

        return RAGQueryResponse(
            query=request.query,
            results=results
        )

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/rag/documents",
    tags=["RAG"],
    summary="List RAG Documents",
    description="Get statistics about indexed documents."
)
async def list_documents():
    """List all uploaded documents."""
    try:
        rag_service = get_rag_service()
        stats = await rag_service.get_stats()
        return stats

    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/rag/documents/{filename}",
    response_model=GenericResponse,
    tags=["RAG"],
    summary="Delete RAG Document",
    description="Remove a document and its chunks from the vector database."
)
async def delete_document(filename: str):
    try:
        rag_service = get_rag_service()
        deleted = await rag_service.delete_document(filename)

        if deleted:
            return GenericResponse(status="success", message=f"Document '{filename}' deleted.")
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== LINE Webhook ==============

@router.post(
    "/webhook/line",
    tags=["Webhooks"],
    summary="LINE Messaging Webhook",
    description="Endpoint for receiving webhooks from LINE Platform."
)
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None)
):
    """
    LINE webhook endpoint.
    
    This receives messages from LINE and responds using the configured LLM.
    """
    line_handler = get_line_handler()

    if not line_handler.is_available():
        raise HTTPException(
            status_code=503,
            detail="LINE integration not configured"
        )

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        # Verify signature
        await line_handler.handle_webhook(body_str, x_line_signature)

        # Parse and process events
        import json
        data = json.loads(body_str)

        for event_data in data.get("events", []):
            if event_data.get("type") == "message":
                if event_data.get("message", {}).get("type") == "text":
                    # Create event object
                    event = MessageEvent.from_dict(event_data)

                    # Process message and generate response
                    response_text = await line_handler.process_text_message(event)

                    # Reply to user
                    await line_handler.reply_message(
                        event.reply_token,
                        response_text
                    )

        return {"status": "ok"}

    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"LINE webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Provider Management ==============

@router.get(
    "/providers",
    tags=["Providers"],
    summary="List LLM Providers",
    description="Get a list of supported LLM providers and their availability."
)
async def list_providers():
    return LLMFactory.get_available_providers()


@router.get(
    "/providers/{provider}/models",
    response_model=ProviderModelsResponse,
    tags=["Providers"],
    summary="List Provider Models",
    description="Get available models for a specific provider (e.g. Ollama models)."
)
async def get_provider_models(provider: str):
    try:
        provider_enum = LLMProvider(provider.lower())

        if provider_enum == LLMProvider.OLLAMA:
            # For Ollama, we can query available models
            import httpx
            from app.core.config import get_settings

            settings = get_settings()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.ollama_base_url}/api/tags",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return ProviderModelsResponse(
                        provider=provider,
                        models=models
                    )

        # For other providers, return configured model
        llm = LLMFactory.create(provider_enum)
        return ProviderModelsResponse(
            provider=provider,
            models=[llm.model_name],
            note="List shows configured model only"
        )

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    except Exception as e:
        logger.error(f"Get models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
