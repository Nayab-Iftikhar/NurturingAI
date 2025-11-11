"""
Tests for message generator service
"""
import pytest
from unittest.mock import patch, MagicMock
from services.message_generator import generate_personalized_message, clean_message_content


class TestMessageGenerator:
    """Test message generator service"""
    
    def test_clean_message_content(self):
        """Test cleaning meta-descriptions from messages"""
        # Test with meta-description
        message = "Here's a personalized follow-up email that re-engages John Doe with Test Project:\n\nActual message content here."
        cleaned = clean_message_content(message)
        assert "Here's a personalized" not in cleaned
        assert "Actual message content here" in cleaned
        
        # Test without meta-description
        message = "Actual message content here."
        cleaned = clean_message_content(message)
        assert cleaned == message
        
        # Test with multiple patterns
        message = "This email re-engages the customer:\n\nMessage content."
        cleaned = clean_message_content(message)
        assert "This email" not in cleaned
        assert "Message content" in cleaned
    
    @patch('services.message_generator.get_llm_candidates')
    def test_generate_personalized_message(self, mock_llm_candidates):
        """Test generating personalized message"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = 'This is a personalized message for the lead.'
        mock_llm.invoke.return_value = mock_response
        mock_llm_candidates.return_value = [('openai', mock_llm)]
        
        lead_data = {
            'name': 'Test Lead',
            'email': 'test@example.com',
            'project_name': 'Test Project',
            'unit_type': '2 bed',
            'budget_min': 500000,
            'budget_max': 1000000,
            'last_conversation_summary': 'Previous discussion about amenities'
        }
        
        message = generate_personalized_message(
            lead_data=lead_data,
            campaign_project='Test Project',
            offer_details='Special discount available'
        )
        
        assert message is not None
        assert len(message) > 0
        # Should not contain meta-descriptions
        assert "Here's a personalized" not in message
        assert "This email" not in message
    
    @patch('services.message_generator.get_llm_candidates')
    def test_generate_personalized_message_fallback(self, mock_llm_candidates):
        """Test fallback message when LLM fails"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception('LLM error')
        mock_llm_candidates.return_value = [('openai', mock_llm)]
        
        lead_data = {
            'name': 'Test Lead',
            'email': 'test@example.com',
            'project_name': 'Test Project',
            'unit_type': '2 bed'
        }
        
        message = generate_personalized_message(
            lead_data=lead_data,
            campaign_project='Test Project'
        )
        
        # Should return fallback message
        assert message is not None
        assert 'Test Lead' in message
        assert 'Test Project' in message

