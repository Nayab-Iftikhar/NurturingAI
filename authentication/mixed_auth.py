from ninja.security import HttpBearer
from django.http import HttpRequest
from django.contrib.auth.models import User
from typing import Optional
import jwt
from django.conf import settings


class MixedAuth(HttpBearer):
    """Authentication that supports both JWT (Bearer token) and session-based auth"""
    
    def authenticate(self, request: HttpRequest, token: str = None) -> Optional[User]:
        """Authenticate using JWT token or Django session"""
        # First try JWT token if provided
        if token:
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                user_id = payload.get('user_id')
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        return user
                    except User.DoesNotExist:
                        pass
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass
        
        # Fall back to session-based authentication
        if request.user.is_authenticated:
            return request.user
        
        return None


# Global instance
mixed_auth = MixedAuth()

