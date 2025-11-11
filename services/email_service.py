import logging
import uuid
from typing import Optional
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger(__name__)


def send_personalized_email(to_email: str, subject: str, message: str) -> Optional[str]:
    """
    Send personalized email to lead and return Message-ID for tracking replies.
    
    Returns:
        Message-ID string if successful, None otherwise
    """
    try:
        # For testing/demo: send all emails to nayabiftikhar6633@gmail.com
        test_email = getattr(settings, 'TEST_EMAIL', 'nayabiftikhar6633@gmail.com')
        recipient_email = test_email

        # Add original recipient info to message
        message_with_info = f"[Original Recipient: {to_email}]\n\n{message}"

        # Generate unique Message-ID for email threading
        # Store without angle brackets in DB for easier matching
        # Email clients will add/remove brackets, so we normalize
        message_id = f"{uuid.uuid4()}@nurturingai.local"

        # Check if using console backend
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in email_backend.lower():
            # If using console backend, also print a clear message
            print("\n" + "="*80)
            print("EMAIL SENT (Console Backend - Check terminal output)")
            print("="*80)
            print(f"To: {recipient_email}")
            print(f"From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"Subject: {subject}")
            print(f"Message-ID: {message_id}")
            print("-"*80)
            print(message_with_info)
            print("="*80 + "\n")

        # Use EmailMessage to set custom headers
        # Email clients expect Message-ID with angle brackets
        email = EmailMessage(
            subject=subject,
            body=message_with_info,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        # Set Message-ID with angle brackets for email clients
        # But return/store without brackets for easier matching
        email.extra_headers['Message-ID'] = f"<{message_id}>"
        email.send(fail_silently=False)
        
        # Return Message-ID without brackets for database storage
        return message_id
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        return None

