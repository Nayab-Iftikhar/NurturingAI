from django.db import models


class Lead(models.Model):
    """Represents a sales lead for a real estate project."""

    lead_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    country_code = models.CharField(max_length=5)
    phone = models.CharField(max_length=32)
    project_name = models.CharField(max_length=255)
    unit_type = models.CharField(max_length=255)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=64)
    last_conversation_date = models.DateField(null=True, blank=True)
    last_conversation_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lead_id"]

    def __str__(self) -> str:
        return f"{self.lead_id} - {self.name}"
