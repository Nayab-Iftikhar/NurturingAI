"""
Django management command to periodically check for email replies
This command is designed to be run every minute (via cron or scheduler)
"""
import logging
import time
from django.core.management.base import BaseCommand
from services.email_reply_service import check_email_replies

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Periodically check for email replies (runs continuously, checking every minute)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit (for cron jobs)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between checks (default: 60)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to look back for emails (default: 1)'
        )

    def handle(self, *args, **options):
        run_once = options['once']
        interval = options['interval']
        days = options['days']
        
        if run_once:
            # Single run mode (for cron)
            self.stdout.write(f"Checking for email replies from the last {days} days...")
            try:
                result = check_email_replies(days=days)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {result['processed']} emails, "
                        f"found {result['new_replies']} new replies"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error checking email replies: {e}")
                )
        else:
            # Continuous mode
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starting periodic email reply checker (interval: {interval}s, days: {days})"
                )
            )
            self.stdout.write("Press Ctrl+C to stop")
            
            try:
                while True:
                    try:
                        result = check_email_replies(days=days)
                        if result['new_replies'] > 0:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                                    f"Found {result['new_replies']} new replies"
                                )
                            )
                        else:
                            self.stdout.write(
                                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                                f"No new replies (processed {result['processed']} emails)"
                            )
                    except Exception as e:
                        logger.error(f"Error in periodic check: {e}", exc_info=True)
                        self.stdout.write(
                            self.style.ERROR(
                                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}"
                            )
                        )
                    
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\nStopped periodic checking"))

