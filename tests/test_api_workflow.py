"""
Tests for API workflow endpoints
"""
import pytest
from django.contrib.auth import get_user_model
from leads.models import Lead
from campaigns.models import Campaign, CampaignLead

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication API endpoints"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.client = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up if needed
        pass
    
    def test_register_user(self, client):
        """Test user registration"""
        response = client.post('/api/auth/register', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User'
        }, content_type='application/json')
        
        assert response.status_code == 201
        assert 'access_token' in response.json()
    
    def test_login_user(self, client, test_user):
        """Test user login"""
        response = client.post('/api/auth/login', {
            'username': test_user.username,
            'password': 'testpass123'
        }, content_type='application/json')
        
        assert response.status_code == 200
        assert 'access_token' in response.json()


@pytest.mark.django_db
class TestLeadsAPI:
    """Test leads API endpoints"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_lead = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test leads
        if self.test_lead:
            try:
                self.test_lead.delete()
            except Exception:
                pass
    
    def test_filter_leads(self, authenticated_client, sample_lead_data):
        """Test filtering leads"""
        # Create test lead
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        # Filter leads
        response = authenticated_client.post('/api/leads/filter', {
            'project_name': 'Test Project',
            'status': 'Connected'
        }, content_type='application/json')
        
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'leads' in data
        assert data['count'] >= 1
    
    def test_get_project_names(self, authenticated_client, sample_lead_data):
        """Test getting project names"""
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        response = authenticated_client.get('/api/leads/projects')
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, list)
        assert 'Test Project' in projects
    
    def test_get_unit_types(self, authenticated_client, sample_lead_data):
        """Test getting unit types"""
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        response = authenticated_client.get('/api/leads/unit-types')
        assert response.status_code == 200
        unit_types = response.json()
        assert isinstance(unit_types, list)
        assert '2 bed' in unit_types


@pytest.mark.django_db
class TestCampaignsAPI:
    """Test campaigns API endpoints"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_campaign = None
        self.test_lead = None
        self.test_campaign_lead = None
    
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
    
    def test_create_campaign(self, authenticated_client, test_user, sample_lead_data):
        """Test creating a campaign"""
        # Create test lead
        self.test_lead = Lead.objects.create(**sample_lead_data)
        
        # Create campaign
        response = authenticated_client.post('/api/campaigns/create', {
            'name': 'Test Campaign',
            'project_name': 'Test Project',
            'channel': 'email',
            'offer_details': 'Test offer',
            'lead_ids': [self.test_lead.lead_id]
        }, content_type='application/json')
        
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'Test Campaign'
        assert data['leads_count'] == 1
        
        # Store for cleanup
        self.test_campaign = Campaign.objects.get(id=data['id'])
    
    def test_list_campaigns(self, authenticated_client, test_user, sample_lead_data):
        """Test listing campaigns"""
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
        
        response = authenticated_client.get('/api/campaigns/list')
        assert response.status_code == 200
        campaigns = response.json()
        assert len(campaigns) >= 1
        assert campaigns[0]['name'] == 'Test Campaign'
    
    def test_get_campaign_details(self, authenticated_client, test_user, sample_lead_data):
        """Test getting campaign details"""
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
        
        response = authenticated_client.get(f'/api/campaigns/{self.test_campaign.id}')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Test Campaign'
        assert len(data['leads']) == 1
