from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from django.db.models import Q
from ninja import Router, Schema
from django.conf import settings

from leads.models import Lead
from leads.schemas import (
    LeadFilterSchema,
    LeadResponseSchema,
    LeadFilterResponseSchema,
)
from authentication.jwt_auth import jwt_auth
import jwt
from django.contrib.auth.models import User


router = Router()


@router.post(
    "/filter",
    response={200: LeadFilterResponseSchema, 400: dict, 401: dict},
    auth=None,
)
def filter_leads(request, filters: LeadFilterSchema):
    """
    Filter leads based on criteria
    
    Requires at least 2 filter criteria to be specified.
    """
    # Check authentication - support both JWT and session
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

    if not user:
        return 401, {"error": "Authentication required"}

    # Count how many filters are provided
    filter_count = sum(
        [
            filters.last_conversation_date_from is not None
            or filters.last_conversation_date_to is not None,
            filters.project_name is not None,
            filters.budget_min is not None or filters.budget_max is not None,
            filters.unit_types is not None and len(filters.unit_types) > 0,
            filters.status is not None,
        ]
    )

    if filter_count < 2:
        return 400, {
            "error": "At least 2 filter criteria must be specified",
            "filter_count": filter_count,
        }

    # Build query
    query = Q()

    # Date range filter
    if filters.last_conversation_date_from:
        query &= Q(last_conversation_date__gte=filters.last_conversation_date_from)
    if filters.last_conversation_date_to:
        query &= Q(last_conversation_date__lte=filters.last_conversation_date_to)

    # Project name filter
    if filters.project_name:
        query &= Q(project_name__iexact=filters.project_name)

    # Budget range filter
    if filters.budget_min is not None:
        # Lead's max budget should be >= filter min, or lead's min budget should be >= filter min
        query &= (
            Q(budget_max__gte=filters.budget_min)
            | Q(budget_min__gte=filters.budget_min)
            | (Q(budget_min__isnull=True) & Q(budget_max__isnull=True))
        )
    if filters.budget_max is not None:
        # Lead's min budget should be <= filter max, or lead's max budget should be <= filter max
        query &= (
            Q(budget_min__lte=filters.budget_max)
            | Q(budget_max__lte=filters.budget_max)
            | (Q(budget_min__isnull=True) & Q(budget_max__isnull=True))
        )

    # Unit type filter (multi-select)
    if filters.unit_types and len(filters.unit_types) > 0:
        query &= Q(unit_type__in=filters.unit_types)

    # Status filter
    if filters.status:
        query &= Q(status__iexact=filters.status)

    # Execute query
    leads = Lead.objects.filter(query).order_by("lead_id")

    # Convert to response schema
    lead_responses = [LeadResponseSchema.from_orm(lead) for lead in leads]

    return {
        "count": len(lead_responses),
        "leads": lead_responses,
    }


@router.get("/projects", response={200: List[str], 401: dict}, auth=None)
def get_projects(request):
    """Get list of unique project names"""
    # Check authentication
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

    if not user:
        return 401, {"error": "Authentication required"}

    projects = (
        Lead.objects.values_list("project_name", flat=True)
        .distinct()
        .order_by("project_name")
    )
    return list(projects)


@router.get("/unit-types", response={200: List[str], 401: dict}, auth=None)
def get_unit_types(request):
    """Get list of unique unit types"""
    # Check authentication
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

    if not user:
        return 401, {"error": "Authentication required"}

    unit_types = (
        Lead.objects.values_list("unit_type", flat=True)
        .distinct()
        .order_by("unit_type")
    )
    return list(unit_types)


@router.get("/statuses", response={200: List[str], 401: dict}, auth=None)
def get_statuses(request):
    """Get list of unique lead statuses"""
    # Check authentication
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

    if not user:
        return 401, {"error": "Authentication required"}

    statuses = (
        Lead.objects.values_list("status", flat=True).distinct().order_by("status")
    )
    return list(statuses)

