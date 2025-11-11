from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "lead_id",
        "name",
        "email",
        "project_name",
        "unit_type",
        "status",
        "last_conversation_date",
    )
    search_fields = ("lead_id", "name", "email", "project_name", "unit_type")
    list_filter = ("status", "project_name", "unit_type")
    ordering = ("lead_id",)
    readonly_fields = ("created_at", "updated_at")
