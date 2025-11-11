"""
Custom SMTP email backend that handles SSL certificate verification issues
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings


class CustomSMTPEmailBackend(EmailBackend):
    """Custom SMTP backend that can disable SSL verification for development"""
    
    def __init__(self, *args, **kwargs):
        """Initialize with SSL context disabled if configured"""
        super().__init__(*args, **kwargs)
        # Set SSL context before connection is created
        if getattr(settings, 'EMAIL_SSL_DISABLE_VERIFY', False):
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

