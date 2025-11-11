"""
Tests for campaign followups API endpoints
"""
import pytest
from datetime import datetime
from django.contrib.auth import get_user_model
from campaigns.models import Campaign, CampaignLead, Conversation
from leads.models import Lead

User = get_user_model()


@pytest.mark.django_db
class TestCampaignFollowupsAPI:
    """Test campaign followups API endpoints"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.lead1 = Lead.objects.create(
            lead_id='TEST001',
            name='Test Lead 1',
            email='testlead1@example.com',
            project_name='Test Project'
        )
        self.lead2 = Lead.objects.create(
            lead_id='TEST002',
            name='Test Lead 2',
            email='testlead2@example.com',
            project_name='Test Project'
        )
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            project_name='Test Project',
            channel='email',
            created_by=self.user
        )
        self.campaign_lead1 = CampaignLead.objects.create(
            campaign=self.campaign,
            lead=self.lead1,
            message_sent=True,
            message_sent_at=datetime.now(),
            email_message_id='msg-001'
        )
        self.campaign_lead2 = CampaignLead.objects.create(
            campaign=self.campaign,
            lead=self.lead2,
            message_sent=True,
            message_sent_at=datetime.now(),
            email_message_id='msg-002'
        )
        # Create customer reply for lead1
        self.conversation1 = Conversation.objects.create(
            campaign_lead=self.campaign_lead1,
            sender='customer',
            message='I have a question',
            auto_reply_processed=True
        )
        # Create agent response
        Conversation.objects.create(
            campaign_lead=self.campaign_lead1,
            sender='agent',
            message='Here is the answer',
            agent_tool_used='document_rag'
        )
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        for conv in Conversation.objects.filter(campaign_lead__campaign=self.campaign):
            try:
                conv.delete()
            except Exception:
                pass
        if self.campaign_lead2:
            try:
                self.campaign_lead2.delete()
            except Exception:
                pass
        if self.campaign_lead1:
            try:
                self.campaign_lead1.delete()
            except Exception:
                pass
        if self.campaign:
            try:
                self.campaign.delete()
            except Exception:
                pass
        if self.lead2:
            try:
                self.lead2.delete()
            except Exception:
                pass
        if self.lead1:
            try:
                self.lead1.delete()
            except Exception:
                pass
        if self.user:
            try:
                self.user.delete()
            except Exception:
                pass
    
    def test_get_campaign_followups(self, api_client):
        """Test getting campaign followups"""
        response = api_client.get(
            f'/api/campaigns/{self.campaign.id}/followups',
            HTTP_AUTHORIZATION=f'Bearer {api_client.token}'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'followups' in data
        assert 'total_followups' in data
        assert data['total_followups'] >= 1
        assert len(data['followups']) >= 1
        
        # Check followup structure
        followup = data['followups'][0]
        assert 'campaign_lead_id' in followup
        assert 'lead_name' in followup
        assert 'lead_email' in followup
        assert 'reply_count' in followup
        assert 'last_reply_at' in followup
    
    def test_get_campaign_followups_no_replies(self, api_client):
        """Test getting followups when no replies exist"""
        # Create campaign with no replies
        campaign_no_replies = Campaign.objects.create(
            name='No Replies Campaign',
            project_name='Test Project',
            channel='email',
            created_by=self.user
        )
        
        try:
            response = api_client.get(
                f'/api/campaigns/{campaign_no_replies.id}/followups',
                HTTP_AUTHORIZATION=f'Bearer {api_client.token}'
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total_followups'] == 0
            assert len(data['followups']) == 0
        finally:
            campaign_no_replies.delete()
    
    def test_get_followup_conversation(self, api_client):
        """Test getting conversation thread for a followup"""
        response = api_client.get(
            f'/api/campaigns/{self.campaign.id}/followups/{self.campaign_lead1.id}/conversation',
            HTTP_AUTHORIZATION=f'Bearer {api_client.token}'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'conversation_thread' in data
        assert 'lead' in data
        assert 'campaign' in data
        assert len(data['conversation_thread']) >= 2  # At least customer reply and agent response
        
        # Check conversation structure
        conv = data['conversation_thread'][0]
        assert 'sender' in conv
        assert 'message' in conv
        assert 'created_at' in conv
    
    def test_get_followup_conversation_unauthorized(self, client):
        """Test unauthorized access to followup conversation"""
        # Create another user
        other_user = User.objects.create_user(username='otheruser', email='other@example.com', password='testpass123')
        other_campaign = Campaign.objects.create(
            name='Other Campaign',
            project_name='Other Project',
            channel='email',
            created_by=other_user
        )
        
        try:
            # Try to access other user's campaign
            response = client.get(
                f'/api/campaigns/{other_campaign.id}/followups/{self.campaign_lead1.id}/conversation'
            )
            assert response.status_code == 401
        finally:
            other_campaign.delete()
            other_user.delete()
    
    def test_get_followup_conversation_not_found(self, api_client):
        """Test getting conversation for non-existent campaign lead"""
        response = api_client.get(
            f'/api/campaigns/{self.campaign.id}/followups/99999/conversation',
            HTTP_AUTHORIZATION=f'Bearer {api_client.token}'
        )
        
        assert response.status_code == 400

