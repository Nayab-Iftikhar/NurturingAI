from ninja.security import HttpBearer
from django.http import HttpRequest
from django.contrib.auth.models import User
from typing import Optional


class SessionAuth(HttpBearer):
    """Session-based authentication for Django Ninja (for frontend)"""
    
    def authenticate(self, request: HttpRequest, token: str = None) -> Optional[User]:
        """Authenticate using Django session"""
        if request.user.is_authenticated:
            return request.user
        return None


# Global instance
session_auth = SessionAuth()

