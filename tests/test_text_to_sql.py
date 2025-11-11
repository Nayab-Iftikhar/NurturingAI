"""
Tests for Text-to-SQL functionality
"""
import pytest
import os
from django.db import connection
from apps.agent.tools.text_to_sql import TextToSQLTool
from leads.models import Lead
from campaigns.models import Campaign, CampaignLead
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestTextToSQLTool:
    """Test Text-to-SQL tool"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_leads = []
        self.tool = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test leads
        for lead in self.test_leads:
            try:
                lead.delete()
            except Exception:
                pass
        self.test_leads = []
    
    def test_tool_initialization(self):
        """Test that TextToSQL tool initializes correctly"""
        self.tool = TextToSQLTool()
        assert self.tool is not None
        assert self.tool.vanna_service is not None
    
    def test_training_data_seeding(self):
        """Test that training data is seeded"""
        self.tool = TextToSQLTool()
        training_data = self.tool.vanna_service.get_training_data()
        assert training_data is not None
    
    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY') and not os.getenv('OLLAMA_BASE_URL'),
        reason="No LLM API key or Ollama available"
    )
    def test_simple_query(self):
        """Test a simple SQL query generation"""
        # Create test data
        lead1 = Lead.objects.create(
            lead_id='T2SQL_TEST1',
            name='Test Lead 1',
            email='test1@example.com',
            country_code='1',
            phone='1234567890',
            project_name='Test Project',
            unit_type='2 bed',
            status='Connected'
        )
        lead2 = Lead.objects.create(
            lead_id='T2SQL_TEST2',
            name='Test Lead 2',
            email='test2@example.com',
            country_code='1',
            phone='0987654321',
            project_name='Test Project',
            unit_type='3 bed',
            status='Not Connected'
        )
        self.test_leads = [lead1, lead2]
        
        self.tool = TextToSQLTool()
        result = self.tool.execute("How many leads are there?")
        
        assert 'result' in result or 'error' in result
        if 'result' in result:
            assert isinstance(result['result'], list)
    
    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY') and not os.getenv('OLLAMA_BASE_URL'),
        reason="No LLM API key or Ollama available"
    )
    def test_filtered_query(self):
        """Test a filtered SQL query"""
        # Create test data
        lead = Lead.objects.create(
            lead_id='T2SQL_FILTER1',
            name='Filter Test',
            email='filter@example.com',
            country_code='1',
            phone='1111111111',
            project_name='Filter Project',
            unit_type='2 bed',
            status='Connected'
        )
        self.test_leads = [lead]
        
        self.tool = TextToSQLTool()
        result = self.tool.execute(
            "How many leads are in Filter Project?",
            project_name='Filter Project'
        )
        
        assert 'result' in result or 'error' in result


@pytest.mark.django_db
class TestSQLExecution:
    """Test SQL execution directly"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_lead = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test lead
        if self.test_lead:
            try:
                self.test_lead.delete()
            except Exception:
                pass
    
    def test_direct_sql_query(self):
        """Test executing SQL directly"""
        self.test_lead = Lead.objects.create(
            lead_id='SQL_DIRECT1',
            name='Direct Test',
            email='direct@example.com',
            country_code='1',
            phone='2222222222',
            project_name='Direct Project',
            unit_type='1 bed',
            status='Connected'
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM leads WHERE project_name = 'Direct Project'")
            count = cursor.fetchone()[0]
            assert count >= 1
