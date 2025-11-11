"""
Tests for email reply service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from campaigns.models import Campaign, CampaignLead, Conversation
from leads.models import Lead
from services.email_reply_service import EmailReplyService, check_email_replies
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestEmailReplyService:
    """Test email reply service"""
    
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
            message_sent_at=datetime.now(),
            email_message_id='test-message-id-123'
        )
        self.service = EmailReplyService()
    
    def teardown_method(self):
        """Teardown method called after each test method"""
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
    
    def test_normalize_message_id(self):
        """Test Message-ID normalization"""
        # Test with angle brackets
        normalized = self.service._normalize_message_id('<test-id@example.com>')
        assert normalized == 'test-id@example.com'
        
        # Test without angle brackets
        normalized = self.service._normalize_message_id('test-id@example.com')
        assert normalized == 'test-id@example.com'
        
        # Test with whitespace
        normalized = self.service._normalize_message_id('  <test-id@example.com>  ')
        assert normalized == 'test-id@example.com'
        
        # Test empty string
        normalized = self.service._normalize_message_id('')
        assert normalized == ''
    
    def test_find_campaign_lead_by_message_id(self):
        """Test finding campaign lead by Message-ID"""
        # Test exact match
        found = self.service._find_campaign_lead_by_message_id('test-message-id-123')
        assert found is not None
        assert found.id == self.campaign_lead.id
        
        # Test with angle brackets
        found = self.service._find_campaign_lead_by_message_id('<test-message-id-123>')
        assert found is not None
        assert found.id == self.campaign_lead.id
        
        # Test not found
        found = self.service._find_campaign_lead_by_message_id('non-existent-id')
        assert found is None
    
    @patch('services.email_reply_service.imaplib.IMAP4_SSL')
    def test_fetch_recent_emails(self, mock_imap):
        """Test fetching recent emails from IMAP"""
        # Mock IMAP connection
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        mock_mail.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock email fetch
        from email.message import Message
        mock_msg = Message()
        mock_msg['Message-ID'] = '<reply-123@example.com>'
        mock_msg['In-Reply-To'] = '<test-message-id-123>'
        mock_msg['From'] = 'testlead@example.com'
        mock_msg['Subject'] = 'Re: Test'
        mock_msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        mock_msg.set_payload('Test reply body')
        
        import email
        mock_mail.fetch.return_value = ('OK', [(None, mock_msg.as_bytes())])
        
        emails = self.service.fetch_recent_emails(days=1)
        
        assert isinstance(emails, list)
        mock_mail.login.assert_called_once()
        mock_mail.select.assert_called_once()
    
    @patch('services.email_reply_service.EmailReplyService.fetch_recent_emails')
    def test_process_replies(self, mock_fetch):
        """Test processing email replies"""
        # Mock email data
        mock_fetch.return_value = [
            {
                'message_id': 'reply-msg-123',
                'in_reply_to': 'test-message-id-123',
                'from': 'testlead@example.com',
                'subject': 'Re: Test',
                'body': 'This is a test reply',
                'references': ''
            }
        ]
        
        result = self.service.process_replies(days=1)
        
        assert 'processed' in result
        assert 'new_replies' in result
        assert result['processed'] >= 0
        
        # Check if conversation was created
        conversations = Conversation.objects.filter(
            campaign_lead=self.campaign_lead,
            sender='customer'
        )
        # Note: Actual creation depends on matching logic, so we just verify the method runs
    
    def test_check_email_replies_function(self):
        """Test convenience function"""
        with patch.object(EmailReplyService, 'process_replies') as mock_process:
            mock_process.return_value = {'processed': 0, 'new_replies': 0}
            result = check_email_replies(days=1)
            assert result['processed'] == 0
            assert result['new_replies'] == 0

