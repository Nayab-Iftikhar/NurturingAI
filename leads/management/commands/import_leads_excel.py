import pandas as pd
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand
from django.conf import settings

from leads.models import Lead


def parse_budget(budget_str) -> Optional[Decimal]:
    """Parse budget string to Decimal"""
    if pd.isna(budget_str) or budget_str == "" or str(budget_str).strip() == "":
        return None
    
    try:
        # Handle scientific notation (e.g., 1.37E+08)
        if isinstance(budget_str, (int, float)):
            return Decimal(str(budget_str))
        
        # Remove commas and convert
        cleaned = str(budget_str).replace(",", "").strip()
        if cleaned == "" or cleaned.lower() == "nan":
            return None
        return Decimal(cleaned)
    except (ValueError, AttributeError, TypeError):
        return None


def parse_date(date_value) -> Optional[datetime.date]:
    """Parse date from various formats"""
    if pd.isna(date_value) or date_value == "":
        return None
    
    try:
        # If it's already a datetime/date object
        if isinstance(date_value, (datetime, pd.Timestamp)):
            return date_value.date()
        
        # If it's a string, try parsing
        date_str = str(date_value).strip()
        if date_str == "" or date_str.lower() == "nan":
            return None
        
        # Try DD-MM-YYYY format first
        try:
            return datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            pass
        
        # Try YYYY-MM-DD format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
        
        # Try pandas parsing
        return pd.to_datetime(date_str).date()
    except (ValueError, AttributeError, TypeError):
        return None


def parse_phone(phone_value) -> str:
    """Parse phone number, handling scientific notation"""
    if pd.isna(phone_value) or phone_value == "":
        return ""
    
    try:
        # Handle scientific notation
        if isinstance(phone_value, float):
            # Convert scientific notation to string
            if 'e' in str(phone_value).lower() or 'E' in str(phone_value):
                return f"{int(phone_value):.0f}"
            return str(int(phone_value))
        
        return str(phone_value).strip()
    except (ValueError, AttributeError, TypeError):
        return str(phone_value) if phone_value else ""


class Command(BaseCommand):
    help = "Import leads from Excel file into database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Mock CRM leads for nurturing.xlsx',
            help='Path to Excel file'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing leads before importing'
        )

    def handle(self, *args, **options):
        file_path = Path(settings.BASE_DIR) / options['file']
        
        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(f"Excel file not found at {file_path}")
            )
            return

        # Reset database if requested
        if options['reset']:
            self.stdout.write("Deleting all existing leads...")
            Lead.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("All leads deleted."))

        # Read Excel file
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f"Found {len(df)} rows in Excel file")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error reading Excel file: {e}")
            )
            return

        created_count = 0
        updated_count = 0
        error_count = 0

        # Map Excel columns to model fields
        column_mapping = {
            'Lead ID': 'lead_id',
            'Lead name': 'name',
            'Email': 'email',
            'Country code': 'country_code',
            'Phone': 'phone',
            'Project name': 'project_name',
            'Unit type': 'unit_type',
            'Min. Budget': 'budget_min',
            'Max Budget': 'budget_max',
            'Lead status': 'status',
            'Last conversation date': 'last_conversation_date',
            'Last conversation summary': 'last_conversation_summary',
        }

        for index, row in df.iterrows():
            try:
                # Extract lead_id
                lead_id = str(row.get('Lead ID', '')).strip()
                if not lead_id or pd.isna(row.get('Lead ID')):
                    error_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"Row {index + 1}: Missing Lead ID, skipping")
                    )
                    continue

                # Parse budget values
                budget_min = parse_budget(row.get('Min. Budget', ''))
                budget_max = parse_budget(row.get('Max Budget', ''))

                # Parse date
                last_conversation_date = parse_date(row.get('Last conversation date', ''))

                # Parse phone
                phone = parse_phone(row.get('Phone', ''))

                # Get other fields
                name = str(row.get('Lead name', '')).strip() if not pd.isna(row.get('Lead name')) else ''
                email = str(row.get('Email', '')).strip() if not pd.isna(row.get('Email')) else ''
                country_code = str(row.get('Country code', '')).strip() if not pd.isna(row.get('Country code')) else ''
                project_name = str(row.get('Project name', '')).strip() if not pd.isna(row.get('Project name')) else ''
                unit_type = str(row.get('Unit type', '')).strip() if not pd.isna(row.get('Unit type')) else ''
                status = str(row.get('Lead status', '')).strip() if not pd.isna(row.get('Lead status')) else ''
                summary = str(row.get('Last conversation summary', '')).strip() if not pd.isna(row.get('Last conversation summary')) else ''

                # Create or update lead
                lead, created = Lead.objects.update_or_create(
                    lead_id=lead_id,
                    defaults={
                        "name": name,
                        "email": email,
                        "country_code": country_code,
                        "phone": phone,
                        "project_name": project_name,
                        "unit_type": unit_type,
                        "budget_min": budget_min,
                        "budget_max": budget_max,
                        "status": status,
                        "last_conversation_date": last_conversation_date,
                        "last_conversation_summary": summary,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing row {index + 1} (Lead ID: {row.get('Lead ID', 'unknown')}): {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nImport complete:\n"
                f"  - {created_count} created\n"
                f"  - {updated_count} updated\n"
                f"  - {error_count} errors"
            )
        )

