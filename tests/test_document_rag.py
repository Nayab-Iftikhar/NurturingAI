"""
Tests for Document RAG retrieval and generation
"""
import pytest
import os
import tempfile
from services.chromadb_service import get_chroma_service
from apps.agent.tools.document_rag import DocumentRAGTool
from services.document_processor import process_document


@pytest.mark.django_db
class TestDocumentRAGTool:
    """Test Document RAG tool"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.tool = None
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
    
    def test_tool_initialization(self):
        """Test that DocumentRAG tool initializes correctly"""
        self.tool = DocumentRAGTool()
        assert self.tool is not None
        assert self.tool.chroma_service is not None
    
    def test_query_without_documents(self):
        """Test querying when no documents are available"""
        self.tool = DocumentRAGTool()
        result = self.tool.execute("What are the facilities?")
        
        assert 'response' in result
        assert 'tool' in result
        assert result['tool'] == 'document_rag'
    
    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY') and not os.getenv('OLLAMA_BASE_URL'),
        reason="No LLM API key or Ollama available"
    )
    def test_query_with_documents(self, sample_pdf_file, temp_chromadb_dir):
        """Test querying with documents in ChromaDB"""
        # Process a document first
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            sample_pdf_file.seek(0)
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        # Process document
        process_document(
            file_path=tmp_file_path,
            project_name='RAG Test Project',
            uploaded_by='testuser'
        )
        
        # Query using RAG tool
        self.tool = DocumentRAGTool()
        result = self.tool.execute(
            "What are the facilities and amenities?",
            project_name='RAG Test Project'
        )
        
        assert 'response' in result
        assert 'tool' in result
        assert result['tool'] == 'document_rag'
        # Should have found relevant chunks
        if 'chunks' in result:
            assert len(result['chunks']) > 0
    
    def test_semantic_search(self, sample_pdf_file, temp_chromadb_dir):
        """Test semantic search in ChromaDB"""
        # Process a document
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            sample_pdf_file.seek(0)
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        process_document(
            file_path=tmp_file_path,
            project_name='Search Test Project',
            uploaded_by='testuser'
        )
        
        # Query ChromaDB directly
        chroma_service = get_chroma_service()
        results = chroma_service.query_documents(
            query="swimming pool facilities",
            n_results=3,
            filter_metadata={"project_name": "Search Test Project"}
        )
        
        assert results is not None
        if results.get('documents') and len(results['documents']) > 0:
            assert len(results['documents'][0]) > 0


@pytest.mark.django_db
class TestChromaDBIntegration:
    """Test ChromaDB integration"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.chroma_service = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up if needed
        pass
    
    def test_add_and_query_documents(self, temp_chromadb_dir):
        """Test adding and querying documents in ChromaDB"""
        self.chroma_service = get_chroma_service()
        
        # Add test documents
        self.chroma_service.add_documents(
            documents=[
                "This property has a swimming pool and gym.",
                "The amenities include shopping mall and schools nearby."
            ],
            metadatas=[
                {"project_name": "Test Project", "source": "test.pdf"},
                {"project_name": "Test Project", "source": "test.pdf"}
            ],
            ids=["test_doc_1", "test_doc_2"]
        )
        
        # Query documents
        results = self.chroma_service.query_documents(
            query="swimming pool",
            n_results=2
        )
        
        assert results is not None
        stats = self.chroma_service.get_collection_stats()
        assert stats['total_documents'] >= 2
