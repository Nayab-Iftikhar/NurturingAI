"""
Tests for document upload and ingestion flow
"""
import pytest
import os
import tempfile
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from services.document_processor import extract_text_from_file, chunk_text, process_document
from services.chromadb_service import get_chroma_service


@pytest.mark.django_db
class TestDocumentProcessing:
    """Test document processing functions"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.temp_files = []
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up temp files
        for tmp_file in self.temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except (OSError, IOError):
                pass
        self.temp_files = []
    
    def test_extract_text_from_pdf(self, sample_pdf_file):
        """Test extracting text from PDF"""
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        text = extract_text_from_file(tmp_file_path)
        assert 'Test Property Brochure' in text
        assert 'Swimming pool' in text
        assert 'Amenities' in text
    
    def test_chunk_text(self):
        """Test text chunking"""
        long_text = "This is a test. " * 200  # Create long text
        chunks = chunk_text(long_text, chunk_size=100, chunk_overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
    
    def test_process_document(self, sample_pdf_file, temp_chromadb_dir):
        """Test full document processing pipeline"""
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        result = process_document(
            file_path=tmp_file_path,
            project_name='Test Project',
            uploaded_by='testuser'
        )
        
        assert result['status'] == 'success'
        assert 'document_id' in result
        assert result['chunks_count'] > 0
        assert result['project_name'] == 'Test Project'
        
        # Verify document is in ChromaDB
        chroma_service = get_chroma_service()
        stats = chroma_service.get_collection_stats()
        assert stats['total_documents'] > 0


@pytest.mark.django_db
class TestDocumentAPI:
    """Test document upload API"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.uploaded_project = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up uploaded documents if needed
        if self.uploaded_project:
            try:
                chroma_service = get_chroma_service()
                chroma_service.delete_documents_by_project(self.uploaded_project)
            except Exception:
                pass
    
    def test_upload_document(self, authenticated_client, sample_pdf_file):
        """Test uploading a document via API"""
        sample_pdf_file.seek(0)
        self.uploaded_project = 'Test Project'
        
        response = authenticated_client.post(
            '/api/documents/upload',
            {
                'file': SimpleUploadedFile(
                    'test_brochure.pdf',
                    sample_pdf_file.read(),
                    content_type='application/pdf'
                ),
                'project_name': self.uploaded_project
            },
            format='multipart'
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert 'chunks_count' in data
        assert data['chunks_count'] > 0
    
    def test_get_document_stats(self, authenticated_client):
        """Test getting document statistics"""
        response = authenticated_client.get('/api/documents/stats')
        assert response.status_code == 200
        data = response.json()
        assert 'total_documents' in data
        assert 'collection_name' in data
    
    def test_delete_project_documents(self, authenticated_client, sample_pdf_file):
        """Test deleting documents by project"""
        self.uploaded_project = 'Test Project Delete'
        
        # First upload a document
        sample_pdf_file.seek(0)
        authenticated_client.post(
            '/api/documents/upload',
            {
                'file': SimpleUploadedFile(
                    'test_brochure.pdf',
                    sample_pdf_file.read(),
                    content_type='application/pdf'
                ),
                'project_name': self.uploaded_project
            },
            format='multipart'
        )
        
        # Delete documents
        response = authenticated_client.delete(f'/api/documents/project/{self.uploaded_project}')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
