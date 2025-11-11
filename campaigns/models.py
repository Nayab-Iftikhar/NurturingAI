from django.db import models
from django.contrib.auth.models import User
from leads.models import Lead


class Campaign(models.Model):
    """Represents a marketing campaign targeting specific leads"""
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    name = models.CharField(max_length=255, blank=True)
    project_name = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    offer_details = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name or 'Campaign'} - {self.project_name} ({self.channel})"


class CampaignLead(models.Model):
    """Links leads to campaigns"""
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_leads')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='campaigns')
    message_sent = models.BooleanField(default=False)
    message_sent_at = models.DateTimeField(null=True, blank=True)
    personalized_message = models.TextField(blank=True)
    email_message_id = models.CharField(max_length=500, blank=True, help_text="Email Message-ID header for tracking replies")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['campaign', 'lead']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.campaign} - {self.lead.lead_id}"


class Conversation(models.Model):
    """Stores customer-agent conversations"""
    
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE, related_name='conversations')
    sender = models.CharField(max_length=20, choices=[('customer', 'Customer'), ('agent', 'Agent')])
    message = models.TextField()
    agent_tool_used = models.CharField(max_length=50, blank=True)
    email_message_id = models.CharField(max_length=500, blank=True, help_text="Email Message-ID header")
    email_in_reply_to = models.CharField(max_length=500, blank=True, help_text="Email In-Reply-To header for threading")
    sales_team_notified = models.BooleanField(default=False, help_text="Whether sales team was notified for this conversation")
    auto_reply_processed = models.BooleanField(default=False, help_text="Whether automated reply has been processed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['email_message_id']),
            models.Index(fields=['email_in_reply_to']),
            models.Index(fields=['auto_reply_processed', 'sender']),
        ]
    
    def __str__(self):
        return f"{self.campaign_lead} - {self.sender} - {self.created_at}"
