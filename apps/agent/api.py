"""
Agent API endpoints following RESTful best practices
"""
from typing import List
from django.conf import settings
from django.contrib.auth.models import User
import jwt
from ninja import Router, Schema
from datetime import datetime

from apps.agent.langgraph_agent import get_agent
from campaigns.models import CampaignLead, Conversation

router = Router()


def get_user_from_request(request):
    """Helper to get user from request (JWT or session)"""
    user = None
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("user_id")
            if user_id:
                user = User.objects.get(id=user_id)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            pass

    if not user and request.user.is_authenticated:
        user = request.user

    return user


class AgentQueryRequestSchema(Schema):
    """Schema for agent query request"""
    campaign_lead_id: int
    query: str


class AgentQueryResponseSchema(Schema):
    """Schema for agent query response"""
    response: str
    tool_used: str
    conversation_id: int
    timestamp: datetime


@router.post(
    "/queries",
    response={200: AgentQueryResponseSchema, 400: dict, 401: dict, 404: dict, 500: dict},
    auth=None,  # Will check auth manually to enforce JWT
)
def create_agent_query(request, data: AgentQueryRequestSchema):
    """
    Submit a new user query to the agent
    
    POST /api/agent/queries
    
    This endpoint:
    1. Validates JWT authentication (mandatory)
    2. Processes the query through the LangGraph agent
    3. Routes to appropriate tool (Text-to-SQL or Document RAG)
    4. Stores conversation history
    5. Returns agent response
    
    Status Codes:
    - 200 OK: Query processed successfully
    - 400 Bad Request: Invalid request data
    - 401 Unauthorized: Missing or invalid JWT token
    - 404 Not Found: Campaign lead not found
    - 500 Internal Server Error: Agent processing error
    """
    # Mandatory JWT authentication check
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Unauthorized", "message": "JWT token is required"}

    # Validate request data
    if not data.query or not data.query.strip():
        return 400, {"error": "Bad Request", "message": "Query cannot be empty"}

    if data.campaign_lead_id <= 0:
        return 400, {"error": "Bad Request", "message": "Invalid campaign_lead_id"}

    # Get campaign lead
    try:
        campaign_lead = CampaignLead.objects.select_related(
            'campaign', 'lead'
        ).get(id=data.campaign_lead_id)
    except CampaignLead.DoesNotExist:
        return 404, {"error": "Not Found", "message": "Campaign lead not found"}

    # Store customer message
    try:
        customer_conversation = Conversation.objects.create(
            campaign_lead=campaign_lead,
            sender='customer',
            message=data.query.strip()
        )
    except Exception as e:
        return 500, {
            "error": "Internal Server Error",
            "message": f"Failed to store customer message: {str(e)}"
        }

    # Process query through LangGraph agent
    try:
        agent = get_agent()
        result = agent.query(
            query=data.query.strip(),
            project_name=campaign_lead.campaign.project_name
        )
    except Exception as e:
        return 500, {
            "error": "Internal Server Error",
            "message": f"Agent processing failed: {str(e)}"
        }

    # Store agent response
    try:
        agent_conversation = Conversation.objects.create(
            campaign_lead=campaign_lead,
            sender='agent',
            message=result['response'],
            agent_tool_used=result.get('tool_used', 'document_rag')
        )
    except Exception as e:
        return 500, {
            "error": "Internal Server Error",
            "message": f"Failed to store agent response: {str(e)}"
        }

    # Return response
    return {
        "response": result['response'],
        "tool_used": result.get('tool_used', 'document_rag'),
        "conversation_id": agent_conversation.id,
        "timestamp": agent_conversation.created_at
    }


@router.get(
    "/queries/{conversation_id}",
    response={200: dict, 401: dict, 404: dict},
    auth=None,  # Will check auth manually to enforce JWT
)
def get_agent_query(request, conversation_id: int):
    """
    Get a specific agent query conversation
    
    GET /api/agent/queries/{conversation_id}
    
    Status Codes:
    - 200 OK: Conversation retrieved successfully
    - 401 Unauthorized: Missing or invalid JWT token
    - 404 Not Found: Conversation not found
    """
    # Mandatory JWT authentication check
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Unauthorized", "message": "JWT token is required"}

    try:
        conversation = Conversation.objects.select_related(
            'campaign_lead__campaign',
            'campaign_lead__lead'
        ).get(id=conversation_id)
    except Conversation.DoesNotExist:
        return 404, {"error": "Not Found", "message": "Conversation not found"}

    return {
        "id": conversation.id,
        "campaign_lead_id": conversation.campaign_lead.id,
        "sender": conversation.sender,
        "message": conversation.message,
        "agent_tool_used": conversation.agent_tool_used,
        "created_at": conversation.created_at
    }


@router.get(
    "/queries",
    response={200: List[dict], 401: dict, 400: dict},
    auth=None,  # Will check auth manually to enforce JWT
)
def list_agent_queries(request, campaign_lead_id: int = None):
    """
    List agent query conversations
    
    GET /api/agent/queries?campaign_lead_id={id}
    
    Query Parameters:
    - campaign_lead_id (optional): Filter by campaign lead ID
    
    Status Codes:
    - 200 OK: Conversations retrieved successfully
    - 400 Bad Request: Invalid query parameters
    - 401 Unauthorized: Missing or invalid JWT token
    """
    # Mandatory JWT authentication check
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Unauthorized", "message": "JWT token is required"}

    # If viewing a specific conversation, check for new email replies first
    if campaign_lead_id:
        if campaign_lead_id <= 0:
            return 400, {"error": "Bad Request", "message": "Invalid campaign_lead_id"}
        
        # Check for new email replies for this campaign lead
        try:
            from services.email_reply_service import check_email_replies
            from campaigns.models import CampaignLead
            from datetime import datetime, timedelta
            
            # Get the campaign lead to check its last message sent time
            try:
                campaign_lead = CampaignLead.objects.select_related('campaign').get(id=campaign_lead_id)
                
                # Verify user has access to this campaign
                if campaign_lead.campaign.created_by != user:
                    return 401, {"error": "Unauthorized", "message": "Access denied to this campaign lead"}
                
                # Check for replies from the last 7 days (or since last message sent)
                if campaign_lead.message_sent_at:
                    days_since_sent = (datetime.now(campaign_lead.message_sent_at.tzinfo) - campaign_lead.message_sent_at).days + 1
                    days_to_check = min(days_since_sent, 7)  # Check up to 7 days
                else:
                    days_to_check = 1  # Default to 1 day if no message sent
                
                # Trigger email reply check (non-blocking, quick check)
                check_email_replies(days=days_to_check)
            except CampaignLead.DoesNotExist:
                return 400, {"error": "Bad Request", "message": "Campaign lead not found"}
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error checking for new replies when viewing conversation: {e}")

    # Build query
    queryset = Conversation.objects.select_related(
        'campaign_lead__campaign',
        'campaign_lead__lead'
    ).all()

    if campaign_lead_id:
        queryset = queryset.filter(campaign_lead_id=campaign_lead_id)

    # Order by creation date (newest first)
    conversations = queryset.order_by('-created_at')[:100]  # Limit to 100

    return [
        {
            "id": conv.id,
            "campaign_lead_id": conv.campaign_lead.id,
            "sender": conv.sender,
            "message": conv.message,
            "agent_tool_used": conv.agent_tool_used,
            "created_at": conv.created_at,
            "campaign_id": conv.campaign_lead.campaign.id,
            "campaign_name": conv.campaign_lead.campaign.name or conv.campaign_lead.campaign.project_name,
            "lead_id": conv.campaign_lead.lead.lead_id,
            "lead_name": conv.campaign_lead.lead.name,
            "lead_email": conv.campaign_lead.lead.email,
            "project_name": conv.campaign_lead.campaign.project_name
        }
        for conv in conversations
    ]

