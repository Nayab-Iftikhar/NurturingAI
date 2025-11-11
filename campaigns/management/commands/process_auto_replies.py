"""
Django management command to process pending automated replies
"""
import logging
from django.core.management.base import BaseCommand
from campaigns.models import Conversation
from services.automated_reply_service import get_automated_reply_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending customer replies and generate automated responses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of conversations to process (default: 50)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing of already processed conversations'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        
        # Get pending customer conversations
        queryset = Conversation.objects.filter(
            sender='customer',
            auto_reply_processed=False if not force else True
        ).select_related('campaign_lead__lead', 'campaign_lead__campaign')[:limit]
        
        total = queryset.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No pending conversations to process."))
            return
        
        self.stdout.write(f"Processing {total} conversation(s)...")
        
        service = get_automated_reply_service()
        processed = 0
        errors = 0
        
        for conversation in queryset:
            try:
                result = service.process_customer_reply(conversation)
                
                # Mark as processed
                conversation.auto_reply_processed = True
                conversation.save(update_fields=['auto_reply_processed'])
                
                action = result.get('action_taken', 'unknown')
                self.stdout.write(
                    f"  ✓ Conversation {conversation.id}: {action} "
                    f"(intent: {result.get('intent', 'unknown')})"
                )
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing conversation {conversation.id}: {e}", exc_info=True)
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Conversation {conversation.id}: {str(e)}")
                )
                errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted: {processed} processed, {errors} errors"
            )
        )

