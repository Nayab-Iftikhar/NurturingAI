from ninja import Router, Schema, File, Form
from ninja.files import UploadedFile
from typing import Optional, List, Dict
from django.conf import settings
from django.contrib.auth.models import User
from services.document_processor import process_document
from services.chromadb_service import get_chroma_service
from services.vanna_service import get_vanna_service
import jwt
import os
import tempfile


router = Router()


def get_user_from_request(request) -> Optional[User]:
    """
    Helper function to get user from request, supporting both JWT and session authentication.
    
    Returns:
        User object if authenticated, None otherwise
    """
    user = None
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    # Try JWT authentication first
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get('user_id')
            if user_id:
                user = User.objects.get(id=user_id)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            pass
    
    # Fall back to session authentication
    if not user and request.user.is_authenticated:
        user = request.user
    
    return user


class DocumentUploadSchema(Schema):
    project_name: str


class DocumentUploadResponse(Schema):
    success: bool
    message: str
    document_id: Optional[str] = None
    chunks_count: Optional[int] = None
    file_name: Optional[str] = None


class DocumentStatsResponse(Schema):
    total_documents: int
    collection_name: str


@router.post(
    "/upload", 
    response={201: DocumentUploadResponse, 400: dict, 401: dict}, 
    auth=None  # Will check auth manually to support both JWT and session
)
def upload_document(
    request, 
    file: UploadedFile = File(...), 
    project_name: str = Form(...)
):
    """
    Upload and process property brochure document
    
    This endpoint:
    1. Accepts file upload (PDF, TXT, DOCX, DOC)
    2. Extracts text from the file
    3. Chunks the text using recursive splitting
    4. Generates embeddings using sentence-transformers
    5. Stores vectors, chunks, and metadata in ChromaDB
    
    Supports both JWT (Bearer token) and session-based authentication.
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.txt', '.docx', '.doc']
        file_ext = os.path.splitext(file.name)[1].lower()
        
        if file_ext not in allowed_extensions:
            return 400, {
                "success": False,
                "message": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            }
        
        if not project_name or not project_name.strip():
            return 400, {
                "success": False,
                "message": "project_name is required"
            }
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # Process document (extract, chunk, embed, store)
            result = process_document(
                file_path=tmp_file_path,
                project_name=project_name.strip(),
                uploaded_by=user.username if user else None
            )
            
            return 201, {
                "success": True,
                "message": f"Document processed and stored successfully. Created {result['chunks_count']} chunks.",
                "document_id": result['document_id'],
                "chunks_count": result['chunks_count'],
                "file_name": result['file_name']
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    except ValueError as e:
        return 400, {
            "success": False,
            "message": str(e)
        }
    except Exception as e:
        return 400, {
            "success": False,
            "message": f"Error processing document: {str(e)}"
        }


@router.get("/stats", response={200: DocumentStatsResponse, 401: dict}, auth=None)
def get_document_stats(request):
    """Get statistics about stored documents"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        chroma_service = get_chroma_service()
        stats = chroma_service.get_collection_stats()
        return stats
    except Exception as e:
        return 200, {
            "total_documents": 0,
            "collection_name": "brochures",
            "error": str(e)
        }


@router.delete("/project/{project_name}", response={200: dict, 400: dict, 401: dict}, auth=None)
def delete_project_documents(request, project_name: str):
    """Delete all documents for a specific project"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        chroma_service = get_chroma_service()
        deleted_count = chroma_service.delete_documents_by_project(project_name)
        return {
            "success": True,
            "message": f"Deleted {deleted_count} document chunks for project '{project_name}'",
            "deleted_count": deleted_count
        }
    except Exception as e:
        return 400, {
            "success": False,
            "message": f"Error deleting documents: {str(e)}"
        }


@router.get("/collections", response={200: List[Dict], 401: dict}, auth=None)
def get_collections(request):
    """Get all ChromaDB collections with their metadata"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        chroma_service = get_chroma_service()
        collections = chroma_service.get_all_collections()
        return collections
    except Exception:
        # Return empty list on error
        return 200, []


@router.get("/contents/brochures", response={200: Dict, 401: dict}, auth=None)
def get_brochure_contents(request, limit: Optional[int] = None):
    """Get all documents from the brochures collection"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        chroma_service = get_chroma_service()
        results = chroma_service.get_all_documents(limit=limit)
        
        # Format results for frontend
        documents = []
        ids = results.get('ids', [])
        docs = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        
        for i, doc_id in enumerate(ids):
            documents.append({
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {}
            })
        
        return {
            "collection": "brochures",
            "total": len(documents),
            "documents": documents
        }
    except Exception as e:
        return 200, {
            "collection": "brochures",
            "total": 0,
            "documents": [],
            "error": str(e)
        }


@router.get("/contents/vanna", response={200: Dict, 401: dict}, auth=None)
def get_vanna_contents(request):
    """Get all training data from the Vanna collection"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        vanna_service = get_vanna_service()
        results = vanna_service.get_training_data()
        
        # Format results for frontend
        documents = []
        ids = results.get('ids', [])
        docs = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        
        for i, doc_id in enumerate(ids):
            documents.append({
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {}
            })
        
        return {
            "collection": "vanna_training",
            "total": len(documents),
            "documents": documents
        }
    except Exception as e:
        return 200, {
            "collection": "vanna_training",
            "total": 0,
            "documents": [],
            "error": str(e)
        }

