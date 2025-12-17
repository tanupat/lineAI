import os
import shutil
from typing import List, Optional, Tuple
from fastapi import UploadFile
from langchain_core.documents import Document
from app.rag.document_processor import DocumentProcessor
from app.rag.vector_store import VectorStore
from app.core.config import get_settings


class RAGService:
    """Service for RAG operations."""

    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.settings = get_settings()

        # Ensure upload directory exists
        os.makedirs(self.settings.upload_dir, exist_ok=True)

    async def upload_document(self, file: UploadFile) -> Tuple[str, int]:
        """
        Upload and process a document.

        Args:
            file: Uploaded file

        Returns:
            Tuple of (filename, chunks_created)
        """
        filename = file.filename

        # Validate file type
        if not self.document_processor.is_supported(filename):
            supported = self.document_processor.get_supported_extensions()
            raise ValueError(
                f"Unsupported file type. Supported: {', '.join(supported)}"
            )

        # Validate file size
        content = await file.read()
        if len(content) > self.settings.max_file_size:
            max_mb = self.settings.max_file_size / (1024 * 1024)
            raise ValueError(f"File too large. Maximum size: {max_mb}MB")

        # Save file
        file_path = os.path.join(self.settings.upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        try:
            # Process document
            chunks = await self.document_processor.process_file(file_path, filename)

            # Add to vector store
            num_chunks = await self.vector_store.add_documents(chunks)

            return filename, num_chunks

        except Exception as e:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    async def query(
        self,
        query: str,
        top_k: int = 5
    ) -> List[dict]:
        """
        Query the RAG system.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of results with content and metadata
        """
        results = await self.vector_store.search_with_scores(query, top_k)

        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "score": float(score)
            }
            for doc, score in results
        ]

    async def get_context_for_query(
        self,
        query: str,
        top_k: int = 3
    ) -> Tuple[str, List[str]]:
        """
        Get context for a query to use with LLM.

        Args:
            query: User query
            top_k: Number of chunks to retrieve

        Returns:
            Tuple of (context_string, list_of_sources)
        """
        results = await self.query(query, top_k)

        if not results:
            return "", []

        # Build context string
        context_parts = []
        sources = set()

        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Document {i}] (Source: {result['source']})\n{result['content']}"
            )
            sources.add(result["source"])

        context = "\n\n---\n\n".join(context_parts)
        return context, list(sources)

    async def delete_document(self, filename: str) -> bool:
        """
        Delete a document from the RAG system.

        Args:
            filename: Name of the file to delete

        Returns:
            True if successful
        """
        # Delete from vector store
        deleted = await self.vector_store.delete_by_source(filename)

        # Delete physical file
        file_path = os.path.join(self.settings.upload_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        return deleted

    async def list_documents(self) -> List[str]:
        """
        List all documents in the RAG system.

        Returns:
            List of document filenames
        """
        return await self.vector_store.get_all_sources()

    async def get_stats(self) -> dict:
        """
        Get RAG system statistics.

        Returns:
            Dict with stats
        """
        sources = await self.vector_store.get_all_sources()
        count = await self.vector_store.get_document_count()

        return {
            "total_chunks": count,
            "total_documents": len(sources),
            "documents": sources
        }
