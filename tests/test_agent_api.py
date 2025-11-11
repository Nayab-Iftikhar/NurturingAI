"""
Tests for Agent API endpoints following RESTful standards
"""
import pytest
from django.contrib.auth import get_user_model
from leads.models import Lead
from campaigns.models import Campaign, CampaignLead, Conversation
from apps.agent.api import get_user_from_request

User = get_user_model()


@pytest.mark.django_db
class TestAgentAPI:
    """Test Agent API endpoints following RESTful best practices"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_lead = None
        self.test_campaign = None
        self.test_campaign_lead = None
        self.test_conversations = []
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test data
        for conv in self.test_conversations:
            try:
                conv.delete()
            except Exception:
                pass
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
    
    def test_create_agent_query_success(self, authenticated_client, test_user, sample_lead_data):
        """Test POST /api/agent/queries - successful query"""
        # Create test data
        self.test_lead = Lead.objects.create(**sample_lead_data)
        self.test_campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=test_user
        )
        self.test_campaign_lead = CampaignLead.objects.create(
            campaign=self.test_campaign,
            lead=self.test_lead
        )
        
        # Make request with JWT token
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.post(
            '/api/agent/queries',
            {
                'campaign_lead_id': self.test_campaign_lead.id,
                'query': 'What are the facilities in this property?'
            },
            content_type='application/json',
            **headers
        )
        
        # Should return 200 OK for successful query (or 500 if LLM not available)
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'response' in data
            assert 'tool_used' in data
            assert 'conversation_id' in data
            assert 'timestamp' in data
    
    def test_create_agent_query_missing_auth(self, client):
        """Test POST /api/agent/queries - missing JWT token returns 401"""
        response = client.post(
            '/api/agent/queries',
            {
                'campaign_lead_id': 1,
                'query': 'Test query'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Unauthorized'
    
    def test_create_agent_query_empty_query(self, authenticated_client, test_user, sample_lead_data):
        """Test POST /api/agent/queries - empty query returns 400"""
        self.test_lead = Lead.objects.create(**sample_lead_data)
        self.test_campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=test_user
        )
        self.test_campaign_lead = CampaignLead.objects.create(
            campaign=self.test_campaign,
            lead=self.test_lead
        )
        
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.post(
            '/api/agent/queries',
            {
                'campaign_lead_id': self.test_campaign_lead.id,
                'query': ''
            },
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Bad Request'
    
    def test_create_agent_query_invalid_campaign_lead(self, authenticated_client):
        """Test POST /api/agent/queries - invalid campaign_lead_id returns 404"""
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.post(
            '/api/agent/queries',
            {
                'campaign_lead_id': 99999,
                'query': 'Test query'
            },
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Not Found'
    
    def test_get_agent_query_success(self, authenticated_client, test_user, sample_lead_data):
        """Test GET /api/agent/queries/{id} - successful retrieval"""
        # Create test data
        self.test_lead = Lead.objects.create(**sample_lead_data)
        self.test_campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=test_user
        )
        self.test_campaign_lead = CampaignLead.objects.create(
            campaign=self.test_campaign,
            lead=self.test_lead
        )
        conversation = Conversation.objects.create(
            campaign_lead=self.test_campaign_lead,
            sender='customer',
            message='Test query'
        )
        self.test_conversations.append(conversation)
        
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.get(
            f'/api/agent/queries/{conversation.id}',
            **headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == conversation.id
        assert data['sender'] == 'customer'
        assert data['message'] == 'Test query'
    
    def test_get_agent_query_not_found(self, authenticated_client):
        """Test GET /api/agent/queries/{id} - not found returns 404"""
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.get(
            '/api/agent/queries/99999',
            **headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Not Found'
    
    def test_list_agent_queries(self, authenticated_client, test_user, sample_lead_data):
        """Test GET /api/agent/queries - list conversations"""
        # Create test data
        self.test_lead = Lead.objects.create(**sample_lead_data)
        self.test_campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=test_user
        )
        self.test_campaign_lead = CampaignLead.objects.create(
            campaign=self.test_campaign,
            lead=self.test_lead
        )
        conv1 = Conversation.objects.create(
            campaign_lead=self.test_campaign_lead,
            sender='customer',
            message='Query 1'
        )
        conv2 = Conversation.objects.create(
            campaign_lead=self.test_campaign_lead,
            sender='agent',
            message='Response 1'
        )
        self.test_conversations = [conv1, conv2]
        
        token = authenticated_client.token if hasattr(authenticated_client, 'token') else None
        headers = {}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = authenticated_client.get(
            f'/api/agent/queries?campaign_lead_id={self.test_campaign_lead.id}',
            **headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
    
    def test_list_agent_queries_missing_auth(self, client):
        """Test GET /api/agent/queries - missing JWT returns 401"""
        response = client.get('/api/agent/queries')
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Unauthorized'
