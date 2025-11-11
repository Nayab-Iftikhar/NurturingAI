import logging
from typing import Dict, Any, Optional

from services.chromadb_service import get_chroma_service
from services.llm_utils import get_llm_candidates

logger = logging.getLogger(__name__)


class DocumentRAGTool:
    """Tool for retrieving information from brochure documents using RAG"""
    
    def __init__(self):
        self.chroma_service = get_chroma_service()
    
    def execute(self, query: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a RAG query against brochure documents
        
        Args:
            query: Natural language query about the property/brochure
            project_name: Optional project name to filter results
            
        Returns:
            Dict with 'chunks', 'response', and 'tool' keys
        """
        try:
            # Build filter if project name provided
            filter_metadata = None
            if project_name:
                filter_metadata = {"project_name": project_name}
            
            # Query ChromaDB
            results = self.chroma_service.query_documents(
                query=query,
                n_results=5,
                filter_metadata=filter_metadata
            )
            
            # Extract relevant chunks
            chunks = []
            if results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    chunks.append({
                        "text": doc,
                        "source": metadata.get("source", "Unknown"),
                        "project": metadata.get("project_name", "Unknown")
                    })
            
            if not chunks:
                return {
                    "chunks": [],
                    "response": "I couldn't find relevant information about that in the available brochures. Please try rephrasing your question or contact our sales team for more details.",
                    "tool": "document_rag"
                }
            
            # Generate response using LLM
            context = "\n\n".join([f"[From {chunk['source']}]: {chunk['text']}" for chunk in chunks])

            prompt = f"""Based on the following information from property brochures, answer the user's question.

Context from brochures:
{context}

User Question: {query}

Provide a helpful, accurate answer based only on the information provided. If the information doesn't fully answer the question, say so. Be conversational and friendly."""

            llm_candidates = get_llm_candidates()
            errors = []

            for provider, llm in llm_candidates:
                try:
                    response = llm.invoke(prompt)
                    natural_response = getattr(response, "content", str(response)).strip()

                    return {
                        "chunks": chunks,
                        "response": natural_response,
                        "tool": "document_rag",
                        "provider": provider,
                    }
                except Exception as exc:  # pragma: no cover - fallback
                    logger.warning("DocumentRAG provider %s failed: %s", provider, exc)
                    errors.append(f"{provider}: {exc}")
                    continue

            logger.error("All LLM providers failed for Document RAG: %s", "; ".join(errors))
            return {
                "chunks": chunks,
                "response": "I couldn't process the brochure information due to an internal error. Please try again later.",
                "tool": "document_rag",
                "error": "All LLM providers failed.",
                "details": errors,
            }

        except Exception as e:
            return {
                "error": str(e),
                "tool": "document_rag"
            }

