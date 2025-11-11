"""
Service for automated AI agent replies to customer emails
"""
import logging
from typing import Dict, Optional
from django.conf import settings
from apps.agent.langgraph_agent import RealEstateAgent
from services.intent_classifier import get_intent_classifier
from services.email_service import send_personalized_email
from campaigns.models import Conversation
from leads.models import Lead

logger = logging.getLogger(__name__)


class AutomatedReplyService:
    """Service for generating and sending automated replies to customer emails"""
    
    def __init__(self):
        self.agent = RealEstateAgent()
        self.intent_classifier = get_intent_classifier()
    
    def process_customer_reply(
        self, 
        conversation: Conversation
    ) -> Dict[str, any]:
        """
        Process a customer reply and generate appropriate response.
        
        Args:
            conversation: Conversation object with customer message
            
        Returns:
            Dict with:
            - success: bool
            - action_taken: str ('notified_sales', 'sent_reply', 'skipped')
            - agent_response: str (if reply sent)
            - intent: str
            - notification_sent: bool
        """
        try:
            campaign_lead = conversation.campaign_lead
            lead = campaign_lead.lead
            campaign = campaign_lead.campaign
            customer_message = conversation.message
            
            # Classify intent
            try:
                intent_result = self.intent_classifier.classify_intent(
                    customer_message=customer_message,
                    project_name=campaign.project_name,
                    lead_name=lead.name
                )
                
                intent = intent_result["intent"]
                confidence = intent_result["confidence"]
                goal_type = intent_result.get("goal_type")
                
                logger.info(
                    f"Classified intent for conversation {conversation.id}: "
                    f"{intent} (confidence: {confidence:.2f})"
                )
            except Exception as e:
                logger.error(f"Intent classification failed for conversation {conversation.id}: {e}", exc_info=True)
                # Default to question if classification fails
                intent = "question"
                confidence = 0.5
                goal_type = None
                logger.warning(f"Defaulting to 'question' intent for conversation {conversation.id}")
            
            # If goal reached, notify sales team
            if intent == "goal_reached" and confidence >= 0.7:
                notification_sent = self._notify_sales_team(
                    conversation=conversation,
                    goal_type=goal_type,
                    customer_message=customer_message
                )
                
                # Mark conversation as sales team notified
                conversation.sales_team_notified = True
                conversation.save(update_fields=['sales_team_notified'])
                
                # Send acknowledgment to customer
                acknowledgment = self._generate_acknowledgment(
                    lead=lead,
                    campaign=campaign,
                    goal_type=goal_type
                )
                
                # Send acknowledgment email
                subject = f"Thank you for your interest in {campaign.project_name}"
                message_id = send_personalized_email(
                    to_email=lead.email,
                    subject=subject,
                    message=acknowledgment
                )
                
                # Store acknowledgment in conversation
                if message_id:
                    Conversation.objects.create(
                        campaign_lead=campaign_lead,
                        sender='agent',
                        message=acknowledgment,
                        agent_tool_used='acknowledgment',
                        email_message_id=message_id,
                        email_in_reply_to=conversation.email_message_id if conversation.email_message_id else ""
                    )
                
                return {
                    "success": True,
                    "action_taken": "notified_sales",
                    "agent_response": acknowledgment,
                    "intent": intent,
                    "confidence": confidence,
                    "goal_type": goal_type,
                    "notification_sent": notification_sent
                }
            
            # If question, use agent to generate response
            elif intent == "question" or confidence < 0.7:
                # Use agent to answer the question
                try:
                    agent_response = self.agent.query(
                        query=customer_message,
                        project_name=campaign.project_name
                    )
                    
                    # Add gentle nudge towards goal
                    nudge_message = self._add_goal_nudge(
                        agent_response=agent_response,
                        campaign=campaign,
                        lead=lead
                    )
                    tool_used = agent_response.get('tool_used', 'unknown')
                except Exception as e:
                    logger.error(f"Agent query failed for conversation {conversation.id}: {e}", exc_info=True)
                    # Fallback response if agent fails
                    nudge_message = f"""Hi {lead.name},

Thank you for your message regarding {campaign.project_name}. I'm currently processing your inquiry and will get back to you shortly with detailed information.

If you'd like to schedule a viewing or speak with our sales team, please let me know and I'll connect you right away.

Best regards,
NurturingAI"""
                    tool_used = "fallback"
                
                # Send reply email
                subject = f"Re: {campaign.project_name} - Your Question"
                try:
                    message_id = send_personalized_email(
                        to_email=lead.email,
                        subject=subject,
                        message=nudge_message
                    )
                    
                    if not message_id:
                        logger.error(f"Failed to send email reply for conversation {conversation.id}")
                        return {
                            "success": False,
                            "action_taken": "email_failed",
                            "agent_response": nudge_message,
                            "intent": intent,
                            "confidence": confidence,
                            "error": "Email sending failed",
                            "notification_sent": False
                        }
                    
                    # Store agent response in conversation
                    Conversation.objects.create(
                        campaign_lead=campaign_lead,
                        sender='agent',
                        message=nudge_message,
                        agent_tool_used=tool_used,
                        email_message_id=message_id,
                        email_in_reply_to=conversation.email_message_id if conversation.email_message_id else ""
                    )
                    
                    logger.info(f"Successfully sent automated reply for conversation {conversation.id}")
                    
                    return {
                        "success": True,
                        "action_taken": "sent_reply",
                        "agent_response": nudge_message,
                        "intent": intent,
                        "confidence": confidence,
                        "tool_used": tool_used,
                        "notification_sent": False
                    }
                except Exception as e:
                    logger.error(f"Error sending email reply for conversation {conversation.id}: {e}", exc_info=True)
                    return {
                        "success": False,
                        "action_taken": "email_error",
                        "agent_response": nudge_message,
                        "intent": intent,
                        "confidence": confidence,
                        "error": str(e),
                        "notification_sent": False
                    }
            
            # Default: skip if unclear
            else:
                logger.warning(
                    f"Unclear intent for conversation {conversation.id}, skipping auto-reply"
                )
                return {
                    "success": False,
                    "action_taken": "skipped",
                    "agent_response": None,
                    "intent": intent,
                    "confidence": confidence,
                    "notification_sent": False
                }
                
        except Exception as e:
            logger.error(f"Error processing customer reply: {e}", exc_info=True)
            return {
                "success": False,
                "action_taken": "error",
                "error": str(e),
                "notification_sent": False
            }
    
    def _notify_sales_team(
        self,
        conversation: Conversation,
        goal_type: Optional[str],
        customer_message: str
    ) -> bool:
        """
        Notify sales team that a lead has reached a goal outcome.
        
        Returns:
            bool: True if notification sent successfully
        """
        try:
            campaign_lead = conversation.campaign_lead
            lead = campaign_lead.lead
            campaign = campaign_lead.campaign
            
            # Get sales team email from settings (or use default)
            sales_team_email = getattr(
                settings, 
                'SALES_TEAM_EMAIL', 
                settings.DEFAULT_FROM_EMAIL
            )
            
            goal_description = {
                'viewing': 'Property Viewing',
                'sales_call': 'Sales Call',
                'other': 'Next Step'
            }.get(goal_type, 'Next Step')
            
            notification_subject = f"🚨 Lead Ready: {lead.name} - {goal_description} Request"
            
            notification_body = f"""A lead has expressed interest in taking the next step!

Lead Information:
- Name: {lead.name}
- Email: {lead.email}
- Phone: {lead.phone or 'Not provided'}
- Project: {campaign.project_name}
- Goal Type: {goal_description}

Customer Message:
"{customer_message}"

Campaign Details:
- Campaign: {campaign.name or 'N/A'}
- Channel: {campaign.get_channel_display()}

Please follow up with this lead promptly.

---
This is an automated notification from NurturingAI.
"""
            
            message_id = send_personalized_email(
                to_email=sales_team_email,
                subject=notification_subject,
                message=notification_body
            )
            
            if message_id:
                logger.info(
                    f"Sales team notified for conversation {conversation.id} "
                    f"(goal: {goal_type})"
                )
                return True
            else:
                logger.error(f"Failed to send sales team notification for conversation {conversation.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error notifying sales team: {e}", exc_info=True)
            return False
    
    def _generate_acknowledgment(
        self,
        lead: Lead,
        campaign,
        goal_type: Optional[str]
    ) -> str:
        """Generate acknowledgment message for goal reached"""
        goal_text = {
            'viewing': 'property viewing',
            'sales_call': 'sales call',
            'other': 'next step'
        }.get(goal_type, 'next step')
        
        message = f"""Hi {lead.name},

Thank you for your interest in {campaign.project_name}! We've received your request for a {goal_text} and our sales team will be in touch with you shortly to schedule a convenient time.

In the meantime, if you have any questions, please feel free to reply to this email.

Best regards,
NurturingAI Sales Team"""
        
        return message
    
    def _add_goal_nudge(
        self,
        agent_response: Dict,
        campaign,
        lead: Lead
    ) -> str:
        """Add a gentle nudge towards the goal (viewing/sales call) to agent response"""
        response_text = agent_response.get('response', '')
        
        nudge = f"""

---

I hope this information helps! If you'd like to learn more or schedule a viewing of {campaign.project_name}, please let me know and I'll connect you with our sales team.

Best regards,
NurturingAI"""
        
        return response_text + nudge


def get_automated_reply_service() -> AutomatedReplyService:
    """Get singleton instance of AutomatedReplyService"""
    global _automated_reply_service_instance
    if '_automated_reply_service_instance' not in globals():
        _automated_reply_service_instance = AutomatedReplyService()
    return _automated_reply_service_instance

