from datetime import datetime
from typing import List, Optional
from ninja import Schema
from leads.schemas import LeadResponseSchema


class CreateCampaignSchema(Schema):
    """Schema for creating a campaign"""
    name: Optional[str] = None
    project_name: str
    channel: str  # 'email' or 'whatsapp'
    offer_details: Optional[str] = ""
    lead_ids: List[str]  # List of lead IDs to target


class CampaignResponseSchema(Schema):
    """Schema for campaign response"""
    id: int
    name: Optional[str] = None
    project_name: str
    channel: str
    offer_details: str
    created_by: str
    created_at: datetime
    is_active: bool
    leads_count: int = 0

    class Config:
        from_attributes = True


class CampaignDetailResponseSchema(Schema):
    """Schema for detailed campaign response"""
    id: int
    name: Optional[str] = None
    project_name: str
    channel: str
    offer_details: str
    created_by: str
    created_at: datetime
    is_active: bool
    leads: List[LeadResponseSchema] = []

    class Config:
        from_attributes = True


class GenerateMessagesSchema(Schema):
    """Schema for generating campaign messages"""
    campaign_id: int


# Note: Agent query schemas have been moved to apps/agent/api.py
# This follows RESTful best practices with proper resource organization

