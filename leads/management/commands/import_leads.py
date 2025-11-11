import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand
from django.conf import settings

from leads.models import Lead


def parse_budget(budget_str: str) -> Optional[Decimal]:
    """Parse budget string like '13,00,000' to Decimal"""
    if not budget_str or budget_str.strip() == "":
        return None
    # Remove commas and convert to Decimal
    try:
        cleaned = budget_str.replace(",", "")
        return Decimal(cleaned)
    except (ValueError, AttributeError):
        return None


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string like '10-08-2025' to date object"""
    if not date_str or date_str.strip() == "":
        return None
    try:
        # Format: DD-MM-YYYY
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except (ValueError, AttributeError):
        return None


class Command(BaseCommand):
    help = "Import leads from JSON file into database"

    def handle(self, *args, **options):
        # Load JSON file
        json_path = Path(settings.BASE_DIR) / "data" / "leads.json"
        
        if not json_path.exists():
            self.stdout.write(
                self.style.ERROR(f"Leads JSON file not found at {json_path}")
            )
            return

        with open(json_path, "r", encoding="utf-8") as f:
            leads_data = json.load(f)

        created_count = 0
        updated_count = 0
        error_count = 0

        for lead_data in leads_data:
            try:
                lead_id = lead_data.get("Lead ID")
                if not lead_id:
                    error_count += 1
                    continue

                # Parse budget values
                budget_min = parse_budget(lead_data.get("Min. Budget", ""))
                budget_max = parse_budget(lead_data.get("Max Budget", ""))

                # Parse date
                last_conversation_date = parse_date(
                    lead_data.get("Last conversation date", "")
                )

                # Create or update lead
                lead, created = Lead.objects.update_or_create(
                    lead_id=lead_id,
                    defaults={
                        "name": lead_data.get("Lead name", ""),
                        "email": lead_data.get("Email", ""),
                        "country_code": lead_data.get("Country code", ""),
                        "phone": lead_data.get("Phone", ""),
                        "project_name": lead_data.get("Project name", ""),
                        "unit_type": lead_data.get("Unit type", ""),
                        "budget_min": budget_min,
                        "budget_max": budget_max,
                        "status": lead_data.get("Lead status", ""),
                        "last_conversation_date": last_conversation_date,
                        "last_conversation_summary": lead_data.get(
                            "Last conversation summary", ""
                        ),
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing lead {lead_data.get('Lead ID', 'unknown')}: {e}"
                    )
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created_count} created, {updated_count} updated, {error_count} errors"
            )
        )

