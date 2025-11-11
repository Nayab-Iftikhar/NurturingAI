"""
Tests for automated reply service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from campaigns.models import Campaign, CampaignLead, Conversation
from leads.models import Lead
from services.automated_reply_service import AutomatedReplyService, get_automated_reply_service
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAutomatedReplyService:
    """Test automated reply service"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.lead = Lead.objects.create(
            lead_id='TEST001',
            name='Test Lead',
            email='testlead@example.com',
            project_name='Test Project'
        )
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=self.user
        )
        self.campaign_lead = CampaignLead.objects.create(
            campaign=self.campaign,
            lead=self.lead,
            message_sent=True,
            message_sent_at=datetime.now()
        )
        self.conversation = Conversation.objects.create(
            campaign_lead=self.campaign_lead,
            sender='customer',
            message='I want to schedule a viewing',
            auto_reply_processed=False
        )
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        for conv in Conversation.objects.filter(campaign_lead=self.campaign_lead):
            try:
                conv.delete()
            except Exception:
                pass
        if self.campaign_lead:
            try:
                self.campaign_lead.delete()
            except Exception:
                pass
        if self.campaign:
            try:
                self.campaign.delete()
            except Exception:
                pass
        if self.lead:
            try:
                self.lead.delete()
            except Exception:
                pass
        if self.user:
            try:
                self.user.delete()
            except Exception:
                pass
    
    @patch('services.automated_reply_service.RealEstateAgent')
    @patch('services.automated_reply_service.get_intent_classifier')
    def test_service_initialization(self, mock_intent, mock_agent):
        """Test service initialization"""
        service = AutomatedReplyService()
        assert service.agent is not None
        assert service.intent_classifier is not None
    
    @patch('services.automated_reply_service.send_personalized_email')
    @patch('services.automated_reply_service.RealEstateAgent')
    @patch('services.automated_reply_service.get_intent_classifier')
    def test_process_customer_reply_goal_reached(self, mock_intent_class, mock_agent_class, mock_send_email):
        """Test processing customer reply with goal_reached intent"""
        # Mock intent classifier
        mock_classifier = MagicMock()
        mock_classifier.classify_intent.return_value = {
            'intent': 'goal_reached',
            'confidence': 0.9,
            'goal_type': 'viewing',
            'reasoning': 'Customer wants to schedule viewing'
        }
        mock_intent_class.return_value = mock_classifier
        
        # Mock email sending
        mock_send_email.return_value = 'test-message-id-456'
        
        service = AutomatedReplyService()
        service.intent_classifier = mock_classifier
        
        result = service.process_customer_reply(self.conversation)
        
        assert result['success'] is True
        assert result['action_taken'] == 'notified_sales'
        assert result['intent'] == 'goal_reached'
        assert mock_send_email.called
    
    @patch('services.automated_reply_service.send_personalized_email')
    @patch('services.automated_reply_service.RealEstateAgent')
    @patch('services.automated_reply_service.get_intent_classifier')
    def test_process_customer_reply_question(self, mock_intent_class, mock_agent_class, mock_send_email):
        """Test processing customer reply with question intent"""
        # Mock intent classifier
        mock_classifier = MagicMock()
        mock_classifier.classify_intent.return_value = {
            'intent': 'question',
            'confidence': 0.8,
            'goal_type': None,
            'reasoning': 'Customer asking question'
        }
        mock_intent_class.return_value = mock_classifier
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.query.return_value = {
            'response': 'Here is the answer to your question.',
            'tool_used': 'document_rag'
        }
        mock_agent_class.return_value = mock_agent
        
        # Mock email sending
        mock_send_email.return_value = 'test-message-id-789'
        
        service = AutomatedReplyService()
        service.intent_classifier = mock_classifier
        service.agent = mock_agent
        
        result = service.process_customer_reply(self.conversation)
        
        assert result['success'] is True
        assert result['action_taken'] == 'sent_reply'
        assert result['intent'] == 'question'
        assert mock_agent.query.called
        assert mock_send_email.called
    
    def test_get_automated_reply_service_singleton(self):
        """Test singleton pattern"""
        service1 = get_automated_reply_service()
        service2 = get_automated_reply_service()
        assert service1 is service2

