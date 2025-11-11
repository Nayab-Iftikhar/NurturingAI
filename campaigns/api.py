from typing import List
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
import jwt
from ninja import Router

from campaigns.models import Campaign, CampaignLead, Conversation
from campaigns.schemas import (
    CreateCampaignSchema,
    CampaignResponseSchema,
    CampaignDetailResponseSchema,
    GenerateMessagesSchema,
)
from leads.models import Lead
from leads.schemas import LeadResponseSchema
from services.message_generator import generate_personalized_message
from services.email_service import send_personalized_email
from services.email_reply_service import check_email_replies
from datetime import datetime


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
        except Exception:
            pass

    if not user and request.user.is_authenticated:
        user = request.user

    return user


@router.post(
    "/create",
    response={201: CampaignResponseSchema, 400: dict, 401: dict},
    auth=None,
)
def create_campaign(request, data: CreateCampaignSchema):
    """
    Create a new campaign targeting specific leads
    
    Requires:
    - Campaign project name
    - Message channel (email or whatsapp)
    - List of lead IDs to target
    - Optional: Campaign name, offer details
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    # Validate channel
    if data.channel not in ['email', 'whatsapp']:
        return 400, {"error": "Channel must be 'email' or 'whatsapp'"}

    # Validate that leads exist
    if not data.lead_ids:
        return 400, {"error": "At least one lead ID must be provided"}

    leads = Lead.objects.filter(lead_id__in=data.lead_ids)
    if leads.count() != len(data.lead_ids):
        return 400, {
            "error": "Some lead IDs are invalid",
            "provided": len(data.lead_ids),
            "found": leads.count(),
        }

    # Create campaign
    try:
        with transaction.atomic():
            campaign = Campaign.objects.create(
                name=data.name or f"Campaign - {data.project_name}",
                project_name=data.project_name,
                channel=data.channel,
                offer_details=data.offer_details or "",
                created_by=user,
            )

            # Link leads to campaign
            campaign_leads = []
            for lead in leads:
                campaign_lead, created = CampaignLead.objects.get_or_create(
                    campaign=campaign,
                    lead=lead,
                )
                campaign_leads.append(campaign_lead)

            # Return response
            response_data = {
                "id": campaign.id,
                "name": campaign.name,
                "project_name": campaign.project_name,
                "channel": campaign.channel,
                "offer_details": campaign.offer_details,
                "created_by": user.username,
                "created_at": campaign.created_at,
                "is_active": campaign.is_active,
                "leads_count": len(campaign_leads),
            }

            return 201, response_data

    except Exception as e:
        return 400, {"error": f"Error creating campaign: {str(e)}"}


@router.get(
    "/list",
    response={200: List[CampaignResponseSchema], 401: dict},
    auth=None,
)
def list_campaigns(request):
    """List all campaigns for the authenticated user"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    campaigns = Campaign.objects.filter(created_by=user).order_by("-created_at")
    
    response_data = []
    for campaign in campaigns:
        campaign_data = {
            "id": campaign.id,
            "name": campaign.name,
            "project_name": campaign.project_name,
            "channel": campaign.channel,
            "offer_details": campaign.offer_details,
            "created_by": user.username,
            "created_at": campaign.created_at,
            "is_active": campaign.is_active,
            "leads_count": campaign.campaign_leads.count(),
        }
        response_data.append(campaign_data)

    return response_data


@router.get(
    "/{campaign_id}",
    response={200: CampaignDetailResponseSchema, 404: dict, 401: dict},
    auth=None,
)
def get_campaign(request, campaign_id: int):
    """Get campaign details with associated leads"""
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return 404, {"error": "Campaign not found"}

    # Get associated leads
    campaign_leads = CampaignLead.objects.filter(campaign=campaign).select_related('lead')
    leads = [cl.lead for cl in campaign_leads]

    response_data = {
        "id": campaign.id,
        "name": campaign.name,
        "project_name": campaign.project_name,
        "channel": campaign.channel,
        "offer_details": campaign.offer_details,
        "created_by": user.username,
        "created_at": campaign.created_at,
        "is_active": campaign.is_active,
        "leads": [LeadResponseSchema.from_orm(lead).dict() for lead in leads],
    }

    return response_data


@router.get(
    "/{campaign_id}/followups",
    response={200: dict, 404: dict, 401: dict},
    auth=None,
)
def get_campaign_followups(request, campaign_id: int):
    """
    Get all leads that have replied to campaign emails (followups).
    Returns leads with reply counts and last reply date.
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return 404, {"error": "Campaign not found"}

    # Get campaign leads that have customer replies
    campaign_leads = CampaignLead.objects.filter(
        campaign=campaign
    ).select_related('lead').prefetch_related('conversations')

    followups = []
    for campaign_lead in campaign_leads:
        # Check if there are any customer conversations (replies)
        customer_conversations = campaign_lead.conversations.filter(sender='customer')
        
        if customer_conversations.exists():
            last_reply = customer_conversations.order_by('-created_at').first()
            reply_count = customer_conversations.count()
            
            followups.append({
                "campaign_lead_id": campaign_lead.id,
                "lead_id": campaign_lead.lead.lead_id,
                "lead_name": campaign_lead.lead.name,
                "lead_email": campaign_lead.lead.email,
                "reply_count": reply_count,
                "last_reply_at": last_reply.created_at.isoformat() if last_reply else None,
                "sales_team_notified": any(conv.sales_team_notified for conv in customer_conversations),
            })

    # Sort by last reply date (most recent first)
    followups.sort(key=lambda x: x['last_reply_at'] or '', reverse=True)

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name or campaign.project_name,
        "followups": followups,
        "total_followups": len(followups)
    }


@router.get(
    "/{campaign_id}/followups/{campaign_lead_id}/conversation",
    response={200: dict, 404: dict, 401: dict},
    auth=None,
)
def get_followup_conversation(request, campaign_id: int, campaign_lead_id: int):
    """
    Get full conversation thread for a specific campaign lead.
    Returns all messages between AI agent and customer in chronological order.
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return 404, {"error": "Campaign not found"}

    try:
        campaign_lead = CampaignLead.objects.select_related('lead', 'campaign').get(
            id=campaign_lead_id,
            campaign=campaign
        )
    except CampaignLead.DoesNotExist:
        return 404, {"error": "Campaign lead not found"}

    # Get all conversations for this campaign lead, ordered chronologically
    conversations = Conversation.objects.filter(
        campaign_lead=campaign_lead
    ).order_by('created_at')

    conversation_thread = []
    for conv in conversations:
        conversation_thread.append({
            "id": conv.id,
            "sender": conv.sender,
            "sender_display": "Customer" if conv.sender == "customer" else "AI Agent",
            "message": conv.message,
            "agent_tool_used": conv.agent_tool_used or None,
            "created_at": conv.created_at.isoformat(),
            "sales_team_notified": conv.sales_team_notified,
        })

    return {
        "campaign_lead_id": campaign_lead.id,
        "lead": {
            "lead_id": campaign_lead.lead.lead_id,
            "name": campaign_lead.lead.name,
            "email": campaign_lead.lead.email,
            "phone": campaign_lead.lead.phone or None,
        },
        "campaign": {
            "id": campaign.id,
            "name": campaign.name or campaign.project_name,
            "project_name": campaign.project_name,
        },
        "conversation_thread": conversation_thread,
        "total_messages": len(conversation_thread),
    }


@router.post(
    "/{campaign_id}/generate-messages",
    response={200: dict, 400: dict, 401: dict, 404: dict},
    auth=None,
)
def generate_and_send_messages(request, campaign_id: int):
    """
    Generate personalized messages for all leads in a campaign and send them
    
    This will:
    1. Generate hyper-personalized messages for each lead
    2. Send messages via the campaign's channel (email/whatsapp)
    3. Store messages in the database
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return 404, {"error": "Campaign not found"}

    # Get all campaign leads
    campaign_leads = CampaignLead.objects.filter(
        campaign=campaign,
        message_sent=False
    ).select_related('lead')

    if not campaign_leads.exists():
        return 400, {"error": "No leads found or all messages already sent"}

    sent_count = 0
    failed_count = 0
    errors = []

    for campaign_lead in campaign_leads:
        try:
            lead = campaign_lead.lead
            
            # Generate personalized message
            lead_data = {
                'name': lead.name,
                'email': lead.email,
                'project_name': lead.project_name,
                'unit_type': lead.unit_type,
                'budget_min': float(lead.budget_min) if lead.budget_min else None,
                'budget_max': float(lead.budget_max) if lead.budget_max else None,
                'last_conversation_summary': lead.last_conversation_summary,
            }
            
            message = generate_personalized_message(
                lead_data=lead_data,
                campaign_project=campaign.project_name,
                offer_details=campaign.offer_details
            )
            
            # Store message
            campaign_lead.personalized_message = message
            
            # Send message based on channel
            if campaign.channel == 'email':
                subject = f"Exciting Opportunities at {campaign.project_name}"
                message_id = send_personalized_email(
                    to_email=lead.email,
                    subject=subject,
                    message=message
                )
                
                if message_id:
                    campaign_lead.message_sent = True
                    campaign_lead.message_sent_at = datetime.now()
                    campaign_lead.email_message_id = message_id
                    campaign_lead.save()
                    
                    # Create conversation entry for the sent message
                    Conversation.objects.create(
                        campaign_lead=campaign_lead,
                        sender='agent',
                        message=message,
                        agent_tool_used='message_generation',
                        email_message_id=message_id
                    )
                    
                    sent_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Failed to send email to {lead.email}")
            else:
                # WhatsApp - for now just mark as sent (would integrate WhatsApp API here)
                campaign_lead.message_sent = True
                campaign_lead.message_sent_at = datetime.now()
                campaign_lead.save()
                
                # Create conversation entry for the sent message
                Conversation.objects.create(
                    campaign_lead=campaign_lead,
                    sender='agent',
                    message=message,
                    agent_tool_used='message_generation'
                )
                
                sent_count += 1
                
        except Exception as e:
            failed_count += 1
            errors.append(f"Error processing lead {campaign_lead.lead.lead_id}: {str(e)}")

    return {
        "success": True,
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:5] if errors else [],
        "message": f"Sent {sent_count} messages, {failed_count} failed"
    }


@router.post(
    "/{campaign_id}/regenerate-and-send",
    response={200: dict, 400: dict, 401: dict, 404: dict},
    auth=None,
)
def regenerate_and_send_messages(request, campaign_id: int):
    """
    Regenerate and resend messages for all leads in a campaign.
    
    This will:
    1. Reset message_sent status for all campaign leads
    2. Generate new hyper-personalized messages for each lead
    3. Send messages via the campaign's channel (email/whatsapp)
    4. Store new messages in the database
    
    Useful for testing or retrying failed sends.
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}

    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return 404, {"error": "Campaign not found"}

    # Get all campaign leads (including already sent ones)
    campaign_leads = CampaignLead.objects.filter(
        campaign=campaign
    ).select_related('lead')

    if not campaign_leads.exists():
        return 400, {"error": "No leads found in this campaign"}

    sent_count = 0
    failed_count = 0
    errors = []

    for campaign_lead in campaign_leads:
        try:
            lead = campaign_lead.lead
            
            # Generate new personalized message
            lead_data = {
                'name': lead.name,
                'email': lead.email,
                'project_name': lead.project_name,
                'unit_type': lead.unit_type,
                'budget_min': float(lead.budget_min) if lead.budget_min else None,
                'budget_max': float(lead.budget_max) if lead.budget_max else None,
                'last_conversation_summary': lead.last_conversation_summary,
            }
            
            message = generate_personalized_message(
                lead_data=lead_data,
                campaign_project=campaign.project_name,
                offer_details=campaign.offer_details
            )
            
            # Store new message
            campaign_lead.personalized_message = message
            
            # Send message based on channel
            if campaign.channel == 'email':
                subject = f"Exciting Opportunities at {campaign.project_name}"
                message_id = send_personalized_email(
                    to_email=lead.email,
                    subject=subject,
                    message=message
                )
                
                if message_id:
                    # Reset and update status
                    campaign_lead.message_sent = True
                    campaign_lead.message_sent_at = datetime.now()
                    campaign_lead.email_message_id = message_id
                    campaign_lead.save()
                    
                    # Create new conversation entry for the regenerated message
                    Conversation.objects.create(
                        campaign_lead=campaign_lead,
                        sender='agent',
                        message=message,
                        agent_tool_used='message_generation',
                        email_message_id=message_id
                    )
                    
                    sent_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Failed to send email to {lead.email}")
            else:
                # WhatsApp - for now just mark as sent
                campaign_lead.message_sent = True
                campaign_lead.message_sent_at = datetime.now()
                campaign_lead.save()
                
                # Create new conversation entry
                Conversation.objects.create(
                    campaign_lead=campaign_lead,
                    sender='agent',
                    message=message,
                    agent_tool_used='message_generation'
                )
                
                sent_count += 1
                
        except Exception as e:
            failed_count += 1
            errors.append(f"Error processing lead {campaign_lead.lead.lead_id}: {str(e)}")

    return {
        "success": True,
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:5] if errors else [],
        "message": f"Regenerated and sent {sent_count} messages, {failed_count} failed"
    }


@router.post("/check-replies", response={200: dict, 401: dict}, auth=None)
def check_replies(request):
    """
    Manually trigger checking for email replies.
    This endpoint checks the IMAP inbox for replies to sent emails.
    Query parameter: days (default: 7) - Number of days to look back for emails
    """
    user = get_user_from_request(request)
    if not user:
        return 401, {"error": "Authentication required"}
    
    try:
        days = int(request.GET.get('days', 7))
    except (ValueError, TypeError):
        days = 7
    
    try:
        result = check_email_replies(days=days)
        return {
            "success": True,
            "processed": result['processed'],
            "new_replies": result['new_replies'],
            "errors": result.get('errors', [])
        }
    except Exception as e:
        return 500, {
            "success": False,
            "error": str(e)
        }


# Note: Customer query endpoint has been moved to /api/agent/queries
# This follows RESTful best practices with proper resource naming
# The agent API is now in apps/agent/api.py

