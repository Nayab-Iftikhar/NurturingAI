import chromadb
import logging
from chromadb.config import Settings
from django.conf import settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class ChromaDBService:
    """Service for managing ChromaDB vector store"""
    
    def __init__(self):
        # Ensure directory exists and convert Path to string
        chroma_path = str(settings.CHROMA_PERSIST_DIRECTORY)
        os.makedirs(chroma_path, exist_ok=True)

        # Initialize ChromaDB client with telemetry disabled
        self.client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # Get or create brochure collection
        self.brochure_collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_BROCHURES,
            metadata={"description": "Property brochure documents"}
        )

    def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[Dict], 
        ids: List[str]
    ):
        """Add documents to ChromaDB with embeddings"""
        # Generate embeddings
        embeddings = self.embedding_model.encode(documents).tolist()

        # Add to collection
        self.brochure_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def query_documents(
        self, 
        query: str, 
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """Query documents using semantic search"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()

        # Build where clause if filter provided
        where = filter_metadata if filter_metadata else None

        # Query collection
        results = self.brochure_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where
        )

        return results

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        count = self.brochure_collection.count()
        return {
            "total_documents": count,
            "collection_name": settings.CHROMA_COLLECTION_BROCHURES
        }

    def delete_documents_by_project(self, project_name: str) -> int:
        """Delete all documents for a specific project"""
        try:
            # Get all documents for this project
            results = self.brochure_collection.get(
                where={"project_name": project_name}
            )
            
            if results and results.get('ids'):
                # Delete documents
                self.brochure_collection.delete(ids=results['ids'])
                return len(results['ids'])
            return 0
        except Exception as e:
            logger.error(f"Error deleting documents: {e}", exc_info=True)
            return 0

    def get_all_documents(self, limit: Optional[int] = None) -> Dict:
        """Get all documents from the brochure collection"""
        try:
            if limit:
                results = self.brochure_collection.get(limit=limit)
            else:
                results = self.brochure_collection.get()
            return results
        except Exception as e:
            logger.error(f"Error getting documents: {e}", exc_info=True)
            return {"ids": [], "documents": [], "metadatas": []}

    def get_all_collections(self) -> List[Dict]:
        """Get information about all collections in ChromaDB"""
        try:
            collections = self.client.list_collections()
            collection_info = []
            for collection in collections:
                count = collection.count()
                collection_info.append({
                    "name": collection.name,
                    "count": count,
                    "metadata": collection.metadata or {}
                })
            return collection_info
        except Exception as e:
            logger.error(f"Error getting collections: {e}", exc_info=True)
            return []


# Global instance (lazy initialization to avoid startup warnings)
_chroma_service_instance = None


def get_chroma_service():
    """Get or create ChromaDB service instance (lazy initialization)"""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaDBService()
    return _chroma_service_instance


# For backward compatibility - lazy initialization wrapper
class ChromaServiceProxy:
    """Proxy class for lazy initialization of chroma_service"""
    def __getattr__(self, name):
        service = get_chroma_service()
        return getattr(service, name)


# Create proxy instance that will initialize on first use
chroma_service = ChromaServiceProxy()

