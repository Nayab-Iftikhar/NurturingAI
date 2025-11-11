from datetime import date
from decimal import Decimal
from typing import Optional, List
from ninja import Schema


class LeadFilterSchema(Schema):
    """Schema for filtering leads"""
    last_conversation_date_from: Optional[date] = None
    last_conversation_date_to: Optional[date] = None
    project_name: Optional[str] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    unit_types: Optional[List[str]] = None
    status: Optional[str] = None


class LeadResponseSchema(Schema):
    """Schema for lead response"""
    id: int
    lead_id: str
    name: str
    email: str
    country_code: str
    phone: str
    project_name: str
    unit_type: str
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    status: str
    last_conversation_date: Optional[date] = None
    last_conversation_summary: str

    class Config:
        from_attributes = True


class LeadFilterResponseSchema(Schema):
    """Schema for lead filter response"""
    count: int
    leads: List[LeadResponseSchema]

