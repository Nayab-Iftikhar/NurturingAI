"""
Tests for intent classifier service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.intent_classifier import IntentClassifier, get_intent_classifier


class TestIntentClassifier:
    """Test intent classifier"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        pass
    
    @patch('services.intent_classifier.get_llm_candidates')
    def test_classifier_initialization(self, mock_llm_candidates):
        """Test classifier initialization"""
        mock_llm = MagicMock()
        mock_llm_candidates.return_value = [('openai', mock_llm)]
        
        classifier = IntentClassifier()
        assert classifier.candidates is not None
        assert len(classifier.candidates) > 0
    
    @patch('services.intent_classifier.get_llm_candidates')
    def test_classify_intent_goal_reached(self, mock_llm_candidates):
        """Test intent classification for goal_reached"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"intent": "goal_reached", "confidence": 0.9, "reasoning": "Customer wants viewing", "goal_type": "viewing"}'
        mock_llm.invoke.return_value = mock_response
        mock_llm_candidates.return_value = [('openai', mock_llm)]
        
        classifier = IntentClassifier()
        result = classifier.classify_intent(
            customer_message='I want to schedule a viewing',
            project_name='Test Project',
            lead_name='Test Lead'
        )
        
        assert result['intent'] == 'goal_reached'
        assert result['confidence'] == 0.9
        assert result['goal_type'] == 'viewing'
    
    @patch('services.intent_classifier.get_llm_candidates')
    def test_classify_intent_question(self, mock_llm_candidates):
        """Test intent classification for question"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"intent": "question", "confidence": 0.8, "reasoning": "Customer asking question", "goal_type": null}'
        mock_llm.invoke.return_value = mock_response
        mock_llm_candidates.return_value = [('openai', mock_llm)]
        
        classifier = IntentClassifier()
        result = classifier.classify_intent(
            customer_message='What are the amenities?',
            project_name='Test Project',
            lead_name='Test Lead'
        )
        
        assert result['intent'] == 'question'
        assert result['confidence'] == 0.8
        assert result['goal_type'] is None
    
    @patch('services.intent_classifier.get_llm_candidates')
    def test_classify_intent_fallback(self, mock_llm_candidates):
        """Test intent classification with fallback on error"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception('LLM error')
        mock_llm_candidates.return_value = [('openai', mock_llm), ('ollama', MagicMock())]
        
        classifier = IntentClassifier()
        result = classifier.classify_intent(
            customer_message='Test message',
            project_name='Test Project',
            lead_name='Test Lead'
        )
        
        # Should default to question on error
        assert result['intent'] == 'question'
        assert result['confidence'] == 0.5
    
    def test_get_intent_classifier_singleton(self):
        """Test singleton pattern"""
        with patch('services.intent_classifier.get_llm_candidates') as mock_llm:
            mock_llm.return_value = [('openai', MagicMock())]
            classifier1 = get_intent_classifier()
            classifier2 = get_intent_classifier()
            assert classifier1 is classifier2

