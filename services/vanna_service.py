import chromadb
import logging
from chromadb.config import Settings
from django.conf import settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class VannaChromaDBService:
    """Service for managing Vanna training data in ChromaDB"""
    
    def __init__(self):
        # Ensure directory exists
        chroma_path = str(settings.CHROMA_PERSIST_DIRECTORY)
        os.makedirs(chroma_path, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # Get or create Vanna collection
        self.vanna_collection = self.client.get_or_create_collection(
            name='vanna_training',
            metadata={"description": "Vanna training data (DDL, documentation, SQL examples)"}
        )

    def add_training_data(
        self, 
        documents: List[str], 
        metadatas: List[Dict], 
        ids: List[str]
    ):
        """Add training data to ChromaDB"""
        embeddings = self.embedding_model.encode(documents).tolist()
        self.vanna_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def get_similar_training_data(self, query: str, n_results: int = 5) -> Dict:
        """Get similar training data for a query"""
        query_embedding = self.embedding_model.encode([query]).tolist()
        results = self.vanna_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        return results

    def get_training_data(self) -> Dict:
        """Get all training data"""
        try:
            results = self.vanna_collection.get()
            return results
        except Exception as e:
            logger.error(f"Error getting training data: {e}", exc_info=True)
            return {"ids": [], "documents": [], "metadatas": []}


# Global instance (lazy initialization)
_vanna_service_instance = None


def get_vanna_service():
    """Get or create Vanna service instance"""
    global _vanna_service_instance
    if _vanna_service_instance is None:
        _vanna_service_instance = VannaChromaDBService()
    return _vanna_service_instance

