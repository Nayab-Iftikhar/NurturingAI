"""
Service for capturing email replies via IMAP
"""
import logging
import email
import imaplib
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from django.conf import settings
from campaigns.models import CampaignLead, Conversation

logger = logging.getLogger(__name__)


class EmailReplyService:
    """Service for fetching and processing email replies via IMAP"""
    
    def __init__(self):
        self.imap_host = getattr(settings, 'IMAP_HOST', 'imap.gmail.com')
        self.imap_port = getattr(settings, 'IMAP_PORT', 993)
        self.imap_user = getattr(settings, 'IMAP_USER', '')
        self.imap_password = getattr(settings, 'IMAP_PASSWORD', '')
        self.imap_mailbox = getattr(settings, 'IMAP_MAILBOX', 'INBOX')
        self.imap_use_ssl = getattr(settings, 'IMAP_USE_SSL', True)
    
    def connect(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to IMAP server"""
        try:
            if self.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_host, self.imap_port)
            
            mail.login(self.imap_user, self.imap_password)
            mail.select(self.imap_mailbox)
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}", exc_info=True)
            return None
    
    def fetch_recent_emails(self, days: int = 7) -> List[Dict]:
        """
        Fetch recent emails from the mailbox.
        
        Args:
            days: Number of days to look back for emails
            
        Returns:
            List of email dictionaries with parsed headers and body
        """
        mail = self.connect()
        if not mail:
            return []
        
        emails = []
        try:
            # Search for emails from the last N days
            date_since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE {date_since})')
            
            if status != 'OK':
                logger.warning("Failed to search emails")
                return []
            
            email_ids = messages[0].split()
            
            for email_id in email_ids:
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    # Parse email
                    parsed_email = self._parse_email(email_message)
                    if parsed_email:
                        emails.append(parsed_email)
                except Exception as e:
                    logger.warning(f"Error parsing email {email_id}: {e}")
                    continue
            
            mail.close()
            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)
            try:
                mail.close()
                mail.logout()
            except:
                pass
        
        return emails
    
    def _parse_email(self, email_message: email.message.Message) -> Optional[Dict]:
        """Parse email message into dictionary"""
        try:
            # Extract headers
            message_id = email_message.get('Message-ID', '').strip()
            in_reply_to = email_message.get('In-Reply-To', '').strip()
            references = email_message.get('References', '').strip()
            from_addr = email_message.get('From', '').strip()
            to_addr = email_message.get('To', '').strip()
            subject = email_message.get('Subject', '').strip()
            date_str = email_message.get('Date', '')
            
            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str) if date_str else None
            except:
                email_date = None
            
            # Extract body
            body = self._extract_body(email_message)
            
            return {
                'message_id': message_id,
                'in_reply_to': in_reply_to,
                'references': references,
                'from': from_addr,
                'to': to_addr,
                'subject': subject,
                'date': email_date,
                'body': body,
            }
        except Exception as e:
            logger.error(f"Error parsing email: {e}", exc_info=True)
            return None
    
    def _extract_body(self, email_message: email.message.Message) -> str:
        """Extract text body from email message"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get text/plain or text/html
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            # Not multipart
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        
        return body.strip()
    
    def _normalize_message_id(self, msg_id: str) -> str:
        """
        Normalize Message-ID for comparison.
        Removes angle brackets and extra whitespace.
        """
        if not msg_id:
            return ""
        # Remove angle brackets and strip whitespace
        normalized = msg_id.strip().strip('<>').strip()
        return normalized
    
    def _find_campaign_lead_by_message_id(self, message_id: str) -> Optional[CampaignLead]:
        """
        Find CampaignLead by Message-ID, handling format variations.
        Also checks References header for multiple Message-IDs.
        """
        if not message_id:
            return None
        
        normalized_id = self._normalize_message_id(message_id)
        
        # Try exact match first
        campaign_lead = CampaignLead.objects.filter(
            email_message_id=normalized_id
        ).first()
        
        if campaign_lead:
            return campaign_lead
        
        # Try with angle brackets
        campaign_lead = CampaignLead.objects.filter(
            email_message_id=f"<{normalized_id}>"
        ).first()
        
        if campaign_lead:
            return campaign_lead
        
        # Try without angle brackets (in case stored with brackets)
        if normalized_id.startswith('<') and normalized_id.endswith('>'):
            campaign_lead = CampaignLead.objects.filter(
                email_message_id=normalized_id[1:-1]
            ).first()
            if campaign_lead:
                return campaign_lead
        
        # Try partial match (in case email client modified the domain)
        # Extract UUID part from Message-ID
        import re
        uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', normalized_id, re.IGNORECASE)
        if uuid_match:
            uuid_part = uuid_match.group(1)
            # Search for Message-IDs containing this UUID
            all_campaign_leads = CampaignLead.objects.exclude(email_message_id='')
            for cl in all_campaign_leads:
                if uuid_part.lower() in cl.email_message_id.lower():
                    return cl
        
        return None
    
    def _find_conversation_by_message_id(self, message_id: str) -> Optional[Conversation]:
        """Find Conversation by Message-ID, handling format variations."""
        if not message_id:
            return None
        
        normalized_id = self._normalize_message_id(message_id)
        
        # Try exact match first
        conv = Conversation.objects.filter(
            email_message_id=normalized_id
        ).first()
        
        if conv:
            return conv
        
        # Try with angle brackets
        conv = Conversation.objects.filter(
            email_message_id=f"<{normalized_id}>"
        ).first()
        
        if conv:
            return conv
        
        # Try without angle brackets
        if normalized_id.startswith('<') and normalized_id.endswith('>'):
            conv = Conversation.objects.filter(
                email_message_id=normalized_id[1:-1]
            ).first()
            if conv:
                return conv
        
        return None
    
    def process_replies(self, days: int = 7) -> Dict:
        """
        Process email replies and store them in the database.
        
        Args:
            days: Number of days to look back for emails
            
        Returns:
            Dictionary with processing results
        """
        emails = self.fetch_recent_emails(days=days)
        
        logger.info(f"Fetched {len(emails)} emails from IMAP")
        
        processed_count = 0
        new_replies_count = 0
        skipped_no_reply_header = 0
        skipped_no_match = 0
        errors = []
        
        for email_data in emails:
            try:
                in_reply_to = email_data.get('in_reply_to', '').strip()
                references = email_data.get('references', '').strip()
                message_id = email_data.get('message_id', '').strip()
                
                # Skip if no In-Reply-To or References header (not a reply)
                if not in_reply_to and not references:
                    skipped_no_reply_header += 1
                    continue
                
                # Try to find the original email
                campaign_lead = None
                
                # First, try In-Reply-To header
                if in_reply_to:
                    # In-Reply-To might contain multiple Message-IDs, take the first one
                    in_reply_to_ids = [id.strip() for id in in_reply_to.split() if id.strip()]
                    for reply_id in in_reply_to_ids:
                        campaign_lead = self._find_campaign_lead_by_message_id(reply_id)
                        if campaign_lead:
                            logger.info(f"Found CampaignLead match via In-Reply-To: {reply_id}")
                            break
                        
                        # Try Conversation table
                        original_conv = self._find_conversation_by_message_id(reply_id)
                        if original_conv:
                            campaign_lead = original_conv.campaign_lead
                            logger.info(f"Found Conversation match via In-Reply-To: {reply_id}")
                            break
                
                # If not found, try References header (contains chain of Message-IDs)
                if not campaign_lead and references:
                    ref_ids = [id.strip().strip('<>') for id in references.split() if id.strip()]
                    for ref_id in ref_ids:
                        campaign_lead = self._find_campaign_lead_by_message_id(ref_id)
                        if campaign_lead:
                            logger.info(f"Found CampaignLead match via References: {ref_id}")
                            break
                        
                        original_conv = self._find_conversation_by_message_id(ref_id)
                        if original_conv:
                            campaign_lead = original_conv.campaign_lead
                            logger.info(f"Found Conversation match via References: {ref_id}")
                            break
                
                if not campaign_lead:
                    skipped_no_match += 1
                    logger.debug(f"No match found for email. In-Reply-To: {in_reply_to[:50] if in_reply_to else 'None'}, References: {references[:50] if references else 'None'}")
                    continue
                
                # Check if this reply already exists
                if message_id:
                    normalized_msg_id = self._normalize_message_id(message_id)
                    existing = Conversation.objects.filter(
                        email_message_id=normalized_msg_id
                    ).exists()
                    
                    if not existing:
                        # Also check with angle brackets
                        existing = Conversation.objects.filter(
                            email_message_id=f"<{normalized_msg_id}>"
                        ).exists()
                    
                    if existing:
                        logger.debug(f"Reply already exists: {normalized_msg_id}")
                        continue
                
                # Create conversation entry for the reply
                normalized_msg_id = self._normalize_message_id(message_id) if message_id else ""
                normalized_in_reply_to = self._normalize_message_id(in_reply_to) if in_reply_to else ""
                
                conversation = Conversation.objects.create(
                    campaign_lead=campaign_lead,
                    sender='customer',
                    message=email_data.get('body', ''),
                    email_message_id=normalized_msg_id,
                    email_in_reply_to=normalized_in_reply_to,
                    auto_reply_processed=False,  # Will be processed by automated reply service
                )
                
                logger.info(f"Created conversation entry for reply from {email_data.get('from', 'unknown')}")
                new_replies_count += 1
                processed_count += 1
                
                # Trigger automated reply processing (async, don't block)
                try:
                    from services.automated_reply_service import get_automated_reply_service
                    # Process in background (non-blocking)
                    # In production, you might want to use Celery or similar
                    automated_service = get_automated_reply_service()
                    result = automated_service.process_customer_reply(conversation)
                    conversation.auto_reply_processed = True
                    conversation.save(update_fields=['auto_reply_processed'])
                    logger.info(f"Automated reply processed for conversation {conversation.id}: {result.get('action_taken')}")
                except Exception as e:
                    logger.error(f"Error processing automated reply for conversation {conversation.id}: {e}", exc_info=True)
                    # Don't fail the entire process if auto-reply fails
                
            except Exception as e:
                logger.error(f"Error processing email reply: {e}", exc_info=True)
                errors.append(str(e))
                processed_count += 1
        
        result = {
            'processed': processed_count,
            'new_replies': new_replies_count,
            'skipped_no_reply_header': skipped_no_reply_header,
            'skipped_no_match': skipped_no_match,
            'errors': errors[:10] if errors else []
        }
        
        logger.info(f"Reply processing complete: {result}")
        return result


def check_email_replies(days: int = 7) -> Dict:
    """
    Convenience function to check for email replies.
    
    Args:
        days: Number of days to look back for emails
        
    Returns:
        Dictionary with processing results
    """
    service = EmailReplyService()
    return service.process_replies(days=days)

