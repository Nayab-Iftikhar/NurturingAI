import os
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.chromadb_service import get_chroma_service
import uuid
from pypdf import PdfReader
from docx import Document


def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file formats"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif file_ext in ['.docx', '.doc']:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    elif file_ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def chunk_text(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[str]:
    """Split text into chunks using recursive character splitting"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_text(text)
    return chunks


def process_document(
    file_path: str, 
    project_name: str,
    uploaded_by: Optional[str] = None
) -> Dict:
    """
    Process document: extract, chunk, embed, and store in ChromaDB
    
    Returns:
        dict with document_id, chunks_count, and status
    """
    # Extract text
    text = extract_text_from_file(file_path)
    
    if not text.strip():
        raise ValueError("Document is empty or could not extract text")
    
    # Chunk text
    chunks = chunk_text(text)
    
    if not chunks:
        raise ValueError("No text chunks created from document")
    
    # Prepare metadata and IDs
    document_id = str(uuid.uuid4())
    metadatas = []
    ids = []
    file_name = os.path.basename(file_path)
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"{document_id}_chunk_{i}"
        metadata = {
            "project_name": project_name,
            "document_id": document_id,
            "chunk_index": i,
            "source": file_name,
            "total_chunks": len(chunks)
        }
        
        if uploaded_by:
            metadata["uploaded_by"] = uploaded_by
        
        metadatas.append(metadata)
        ids.append(chunk_id)
    
    # Store in ChromaDB
    chroma_service = get_chroma_service()
    chroma_service.add_documents(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    
    return {
        "document_id": document_id,
        "chunks_count": len(chunks),
        "file_name": file_name,
        "project_name": project_name,
        "status": "success"
    }

