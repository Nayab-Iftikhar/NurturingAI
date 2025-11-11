"""
Service for classifying customer email intent
"""
import logging
from typing import Dict
from services.llm_utils import get_llm_candidates

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies customer email intent to determine next action"""
    
    def __init__(self):
        # Initialize LLM for intent classification with fallback support
        self.candidates = get_llm_candidates(temperature=0.3)
        if not self.candidates:
            raise RuntimeError(
                "No LLM providers configured. Please set OPENAI_API_KEY or ensure Ollama is running."
            )
        self.provider, self.llm = self.candidates[0]
        logger.info("Intent classifier LLM initialized with provider: %s", self.provider)
    
    def classify_intent(
        self, 
        customer_message: str, 
        project_name: str = "",
        lead_name: str = ""
    ) -> Dict[str, any]:
        """
        Classify customer message intent.
        
        Returns:
            Dict with:
            - intent: 'goal_reached' or 'question'
            - confidence: float (0.0 to 1.0)
            - reasoning: str (explanation)
            - goal_type: str (if goal_reached: 'viewing', 'sales_call', or 'other')
        """
        prompt = f"""Analyze this customer email message and classify the intent.

Customer Message: "{customer_message}"
Project: {project_name}
Lead Name: {lead_name}

Classify the intent into one of two categories:

1. **goal_reached**: The customer has clearly expressed intent to:
   - Schedule a property viewing/site visit
   - Book a sales call/meeting
   - Request a callback
   - Express strong buying interest with next steps
   - Ask for contact information to proceed

2. **question**: The customer is asking questions about:
   - Property features, amenities, facilities
   - Pricing, payment plans, offers
   - Location, nearby facilities
   - Unit types, specifications
   - General inquiries that need information retrieval

Respond in JSON format:
{{
    "intent": "goal_reached" or "question",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation",
    "goal_type": "viewing" or "sales_call" or "other" (only if intent is goal_reached, else null)
}}

Be strict: Only classify as "goal_reached" if the customer has clearly expressed intent to take action (viewing, call, meeting). Questions about scheduling or "when can I visit" should be "question" unless they explicitly say "I want to schedule" or "book me a viewing"."""

        # Try each LLM candidate in order (with fallback)
        errors = []
        for provider, llm in self.candidates:
            try:
                response = llm.invoke(prompt)
                content = getattr(response, "content", str(response)).strip()
                
                # Try to parse JSON from response
                import json
                import re
                
                # Extract JSON from response (in case LLM adds extra text)
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    # Fallback: try parsing entire response
                    result = json.loads(content)
                
                # Validate and normalize result
                intent = result.get("intent", "question").lower()
                if intent not in ["goal_reached", "question"]:
                    intent = "question"
                
                confidence = float(result.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                
                reasoning = result.get("reasoning", "")
                goal_type = result.get("goal_type") if intent == "goal_reached" else None
                
                logger.debug(f"Intent classified using {provider}: {intent} (confidence: {confidence:.2f})")
                
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "goal_type": goal_type
                }
                
            except Exception as e:
                logger.warning(f"Intent classification failed with {provider}: {e}")
                errors.append(f"{provider}: {str(e)}")
                continue  # Try next provider
        
        # If all providers failed, default to question
        logger.error(f"All LLM providers failed for intent classification: {'; '.join(errors)}")
        return {
            "intent": "question",
            "confidence": 0.5,
            "reasoning": f"Classification failed with all providers: {'; '.join(errors)}",
            "goal_type": None
        }


def get_intent_classifier() -> IntentClassifier:
    """Get singleton instance of IntentClassifier"""
    global _intent_classifier_instance
    if '_intent_classifier_instance' not in globals():
        _intent_classifier_instance = IntentClassifier()
    return _intent_classifier_instance

