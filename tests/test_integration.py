"""
Integration tests for complete workflows
"""
import pytest
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from leads.models import Lead
from campaigns.models import Campaign, CampaignLead
from services.message_generator import generate_personalized_message
from services.email_service import send_personalized_email

User = get_user_model()


@pytest.mark.django_db
class TestCompleteWorkflow:
    """Test complete end-to-end workflows"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_lead = None
        self.test_campaign = None
        self.test_campaign_lead = None
        self.temp_files = []
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test data
        if self.test_campaign_lead:
            try:
                self.test_campaign_lead.delete()
            except Exception:
                pass
        if self.test_campaign:
            try:
                self.test_campaign.delete()
            except Exception:
                pass
        if self.test_lead:
            try:
                self.test_lead.delete()
            except Exception:
                pass
        # Clean up temp files
        for tmp_file in self.temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except (OSError, IOError):
                pass
        self.temp_files = []
    
    def test_lead_to_campaign_workflow(self, authenticated_client, sample_lead_data):
        """Test complete workflow from lead creation to campaign"""
        # Create lead
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        # Filter leads
        response = authenticated_client.post('/api/leads/filter', {
            'project_name': 'Test Project',
            'status': 'Connected'
        }, content_type='application/json')
        assert response.status_code == 200
        
        # Create campaign
        response = authenticated_client.post('/api/campaigns/create', {
            'name': 'Integration Test Campaign',
            'project_name': 'Test Project',
            'channel': 'email',
            'offer_details': 'Special offer for test',
            'lead_ids': [self.test_lead.lead_id]
        }, content_type='application/json')
        assert response.status_code == 201
        
        campaign_id = response.json()['id']
        self.test_campaign = Campaign.objects.get(id=campaign_id)
        
        # Get campaign details
        response = authenticated_client.get(f'/api/campaigns/{campaign_id}')
        assert response.status_code == 200
        assert response.json()['leads_count'] == 1
    
    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY') and not os.getenv('OLLAMA_BASE_URL'),
        reason="No LLM API key or Ollama available"
    )
    def test_message_generation_workflow(self, sample_lead_data):
        """Test message generation workflow"""
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        # Generate personalized message
        lead_data = {
            'name': self.test_lead.name,
            'email': self.test_lead.email,
            'project_name': self.test_lead.project_name,
            'unit_type': self.test_lead.unit_type,
            'budget_min': float(self.test_lead.budget_min) if self.test_lead.budget_min else None,
            'budget_max': float(self.test_lead.budget_max) if self.test_lead.budget_max else None,
            'last_conversation_summary': self.test_lead.last_conversation_summary,
        }
        
        message = generate_personalized_message(
            lead_data=lead_data,
            campaign_project='Test Campaign Project',
            offer_details='Test offer details'
        )
        
        assert len(message) > 0
        assert 'Test Lead' in message or 'test' in message.lower()
    
    def test_document_to_rag_workflow(self, authenticated_client, sample_pdf_file, temp_chromadb_dir):
        """Test complete document upload to RAG query workflow"""
        import tempfile
        
        # Upload document
        sample_pdf_file.seek(0)
        response = authenticated_client.post(
            '/api/documents/upload',
            {
                'file': SimpleUploadedFile(
                    'integration_test.pdf',
                    sample_pdf_file.read(),
                    content_type='application/pdf'
                ),
                'project_name': 'Integration Test Project'
            },
            format='multipart'
        )
        assert response.status_code == 201
        
        # Query using RAG (if LLM available)
        if os.getenv('OPENAI_API_KEY') or os.getenv('OLLAMA_BASE_URL'):
            from apps.agent.tools.document_rag import DocumentRAGTool
            tool = DocumentRAGTool()
            result = tool.execute(
                "What facilities are available?",
                project_name='Integration Test Project'
            )
            assert 'response' in result
            assert result['tool'] == 'document_rag'
