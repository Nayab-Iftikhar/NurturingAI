from django.contrib import admin
from .models import Campaign, CampaignLead


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_name', 'channel', 'created_by', 'created_at', 'is_active')
    list_filter = ('channel', 'is_active', 'project_name', 'created_at')
    search_fields = ('name', 'project_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'lead', 'message_sent', 'message_sent_at', 'created_at')
    list_filter = ('message_sent', 'campaign', 'created_at')
    search_fields = ('campaign__name', 'lead__lead_id', 'lead__name', 'lead__email')
    readonly_fields = ('created_at',)
