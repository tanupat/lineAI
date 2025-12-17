import logging
from typing import Optional, Dict, List
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    PushMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    UnfollowEvent
)
from linebot.v3.exceptions import InvalidSignatureError
from app.core.config import get_settings
from app.llm.factory import LLMFactory
from app.models.schemas import LLMProvider, ChatMessage
from app.rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class LineHandler:
    """Handler for LINE messaging events."""

    def __init__(self):
        settings = get_settings()
        self.channel_secret = settings.line_channel_secret
        self.channel_access_token = settings.line_channel_access_token

        # Initialize handler
        if self.channel_secret:
            self.handler = WebhookHandler(self.channel_secret)
            self._register_handlers()
        else:
            self.handler = None

        # Initialize API client
        if self.channel_access_token:
            configuration = Configuration(
                access_token=self.channel_access_token
            )
            self.api_client = AsyncApiClient(configuration)
            self.messaging_api = AsyncMessagingApi(self.api_client)
        else:
            self.api_client = None
            self.messaging_api = None

        # Initialize services
        self.rag_service = RAGService()

        # User conversation history (in-memory, consider using Redis/DB for production)
        self.conversations: Dict[str, List[ChatMessage]] = {}

        # Settings
        self.default_provider = LLMProvider(settings.default_llm_provider)
        self.use_rag = True
        self.system_prompt = """You are a helpful AI assistant integrated with LINE chat.
Be concise and friendly in your responses.
If you're provided with context from documents, use that information to answer questions accurately."""

    def _register_handlers(self):
        """Register LINE event handlers."""

        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_text_message(event: MessageEvent):
            # This is called synchronously, but we handle it async in the route
            pass

        @self.handler.add(FollowEvent)
        def handle_follow(event: FollowEvent):
            pass

        @self.handler.add(UnfollowEvent)
        def handle_unfollow(event: UnfollowEvent):
            pass

    def is_available(self) -> bool:
        """Check if LINE integration is configured."""
        return bool(self.channel_secret and self.channel_access_token)

    async def handle_webhook(self, body: str, signature: str):
        """
        Handle incoming webhook from LINE.

        Args:
            body: Request body
            signature: X-Line-Signature header

        Raises:
            InvalidSignatureError: If signature is invalid
        """
        if not self.handler:
            raise ValueError("LINE handler not configured")

        self.handler.handle(body, signature)

    async def process_text_message(
        self,
        event: MessageEvent,
        provider: Optional[LLMProvider] = None,
        use_rag: Optional[bool] = None
    ) -> str:
        """
        Process a text message and generate response.

        Args:
            event: LINE message event
            provider: LLM provider to use
            use_rag: Whether to use RAG

        Returns:
            Generated response
        """
        user_id = event.source.user_id
        user_message = event.message.text

        # Check for special commands
        if user_message.startswith("/"):
            return await self._handle_command(user_message, user_id)

        # Get conversation history
        history = self.conversations.get(user_id, [])

        # Get RAG context if enabled
        context = ""
        sources = []
        if use_rag if use_rag is not None else self.use_rag:
            context, sources = await self.rag_service.get_context_for_query(user_message)

        # Build system prompt with context
        system_prompt = self.system_prompt
        if context:
            system_prompt += f"\n\nRelevant context from documents:\n{context}"

        # Generate response
        llm = LLMFactory.create(provider or self.default_provider)
        response = await llm.generate(
            message=user_message,
            conversation_history=history,
            system_prompt=system_prompt
        )

        # Update conversation history
        history.append(ChatMessage(role="user", content=user_message))
        history.append(ChatMessage(role="assistant", content=response))

        # Keep only last 10 exchanges (20 messages)
        if len(history) > 20:
            history = history[-20:]
        self.conversations[user_id] = history

        return response

    async def _handle_command(self, command: str, user_id: str) -> str:
        """Handle special commands."""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/clear":
            self.conversations[user_id] = []
            return "Conversation history cleared."

        elif cmd == "/help":
            return """Available commands:
/clear - Clear conversation history
/rag on|off - Enable/disable RAG
/provider [ollama|openai|gemini|deepseek] - Switch LLM provider
/docs - List uploaded documents
/help - Show this help"""

        elif cmd == "/rag":
            if len(parts) > 1:
                if parts[1].lower() == "on":
                    self.use_rag = True
                    return "RAG enabled."
                elif parts[1].lower() == "off":
                    self.use_rag = False
                    return "RAG disabled."
            return f"RAG is currently {'enabled' if self.use_rag else 'disabled'}."

        elif cmd == "/provider":
            if len(parts) > 1:
                try:
                    self.default_provider = LLMProvider(parts[1].lower())
                    return f"Switched to {self.default_provider.value} provider."
                except ValueError:
                    return "Invalid provider. Use: ollama, openai, gemini, or deepseek"
            return f"Current provider: {self.default_provider.value}"

        elif cmd == "/docs":
            docs = await self.rag_service.list_documents()
            if docs:
                return "Uploaded documents:\n" + "\n".join(f"- {d}" for d in docs)
            return "No documents uploaded."

        return "Unknown command. Type /help for available commands."

    async def reply_message(self, reply_token: str, text: str):
        """
        Send a reply message.

        Args:
            reply_token: LINE reply token
            text: Message text
        """
        if not self.messaging_api:
            raise ValueError("LINE API not configured")

        # Split long messages (LINE has 5000 char limit)
        messages = []
        while text:
            chunk = text[:5000]
            messages.append(TextMessage(text=chunk))
            text = text[5000:]

        await self.messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages[:5]  # LINE allows max 5 messages
            )
        )

    async def push_message(self, user_id: str, text: str):
        """
        Send a push message to a user.

        Args:
            user_id: LINE user ID
            text: Message text
        """
        if not self.messaging_api:
            raise ValueError("LINE API not configured")

        await self.messaging_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)]
            )
        )
