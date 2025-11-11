"""
Tests for email service
"""
import pytest
from unittest.mock import patch, MagicMock
from services.email_service import send_personalized_email
from django.conf import settings


class TestEmailService:
    """Test email service"""
    
    @patch('services.email_service.EmailMessage')
    @patch('services.email_service.settings')
    def test_send_personalized_email(self, mock_settings, mock_email_message):
        """Test sending personalized email"""
        mock_settings.TEST_EMAIL = 'test@example.com'
        mock_settings.DEFAULT_FROM_EMAIL = 'from@example.com'
        mock_settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        
        mock_email = MagicMock()
        mock_email.send.return_value = None
        mock_email.extra_headers = {}
        mock_email_message.return_value = mock_email
        
        message_id = send_personalized_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            message='Test message body'
        )
        
        assert message_id is not None
        assert '@nurturingai.local' in message_id
        mock_email.send.assert_called_once()
        # Verify Message-ID was set in extra_headers
        assert 'Message-ID' in mock_email.extra_headers
        assert mock_email.extra_headers['Message-ID'] == f'<{message_id}>'
    
    @patch('services.email_service.EmailMessage')
    @patch('services.email_service.settings')
    def test_send_personalized_email_uses_test_email(self, mock_settings, mock_email_message):
        """Test that emails are sent to TEST_EMAIL"""
        mock_settings.TEST_EMAIL = 'test@example.com'
        mock_settings.DEFAULT_FROM_EMAIL = 'from@example.com'
        mock_settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        
        mock_email = MagicMock()
        mock_email.send.return_value = None
        mock_email_message.return_value = mock_email
        
        send_personalized_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            message='Test message body'
        )
        
        # Verify email was sent to TEST_EMAIL, not original recipient
        mock_email_message.assert_called_once()
        call_args = mock_email_message.call_args
        assert call_args[1]['to'] == ['test@example.com']
    
    @patch('services.email_service.EmailMessage')
    @patch('services.email_service.settings')
    def test_send_personalized_email_error_handling(self, mock_settings, mock_email_message):
        """Test error handling in email sending"""
        mock_settings.TEST_EMAIL = 'test@example.com'
        mock_settings.DEFAULT_FROM_EMAIL = 'from@example.com'
        mock_settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        
        mock_email = MagicMock()
        mock_email.send.side_effect = Exception('Email send failed')
        mock_email_message.return_value = mock_email
        
        message_id = send_personalized_email(
            to_email='recipient@example.com',
            subject='Test Subject',
            message='Test message body'
        )
        
        # Should return None on error
        assert message_id is None

