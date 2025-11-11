"""
Django management command to check for email replies
"""
from django.core.management.base import BaseCommand
from services.email_reply_service import check_email_replies


class Command(BaseCommand):
    help = 'Check for email replies and store them in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for emails (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(f"Checking for email replies from the last {days} days...")
        
        try:
            result = check_email_replies(days=days)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nResults:\n"
                    f"  - Processed: {result['processed']} emails\n"
                    f"  - New replies found: {result['new_replies']}\n"
                    f"  - Skipped (no reply header): {result.get('skipped_no_reply_header', 0)}\n"
                    f"  - Skipped (no match found): {result.get('skipped_no_match', 0)}"
                )
            )
            
            if result.get('errors'):
                self.stdout.write(
                    self.style.WARNING(f"\nEncountered {len(result['errors'])} errors:")
                )
                for error in result['errors']:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
        except Exception as e:
            import traceback
            self.stdout.write(
                self.style.ERROR(f"Error checking email replies: {e}\n{traceback.format_exc()}")
            )

