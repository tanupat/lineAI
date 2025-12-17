import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import get_settings


class VectorStore:
    """Vector store for RAG using ChromaDB."""

    _instance: Optional["VectorStore"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        settings = get_settings()

        # Create persist directory if it doesn't exist
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        # Initialize ChromaDB
        self.vector_store = Chroma(
            collection_name="documents",
            embedding_function=self.embeddings,
            persist_directory=settings.chroma_persist_dir
        )

        self._initialized = True

    async def add_documents(self, documents: List[Document]) -> int:
        """
        Add documents to the vector store.

        Args:
            documents: List of Document objects to add

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        self.vector_store.add_documents(documents)
        return len(documents)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Document]:
        """
        Search for similar documents.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of similar documents
        """
        results = self.vector_store.similarity_search(
            query,
            k=top_k,
            filter=filter_dict
        )
        return results

    async def search_with_scores(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[tuple]:
        """
        Search for similar documents with similarity scores.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of (document, score) tuples
        """
        results = self.vector_store.similarity_search_with_score(
            query,
            k=top_k,
            filter=filter_dict
        )
        return results

    async def delete_by_source(self, source: str) -> bool:
        """
        Delete documents by source filename.

        Args:
            source: Source filename to delete

        Returns:
            True if successful
        """
        # Get IDs of documents with matching source
        collection = self.vector_store._collection
        results = collection.get(
            where={"source": source}
        )

        if results["ids"]:
            collection.delete(ids=results["ids"])
            return True
        return False

    async def get_all_sources(self) -> List[str]:
        """
        Get all unique source filenames in the store.

        Returns:
            List of unique source names
        """
        collection = self.vector_store._collection
        results = collection.get()

        sources = set()
        if results["metadatas"]:
            for metadata in results["metadatas"]:
                if "source" in metadata:
                    sources.add(metadata["source"])

        return list(sources)

    async def get_document_count(self) -> int:
        """
        Get the total number of documents in the store.

        Returns:
            Document count
        """
        collection = self.vector_store._collection
        return collection.count()

    def reset(self):
        """Reset the vector store (delete all documents)."""
        self.vector_store._collection.delete(
            where={}
        )
