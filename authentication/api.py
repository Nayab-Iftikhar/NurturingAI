from ninja import Router, Schema
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .jwt_auth import create_access_token
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional

router = Router()


class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""


class LoginSchema(Schema):
    username: str
    password: str


class ForgotPasswordSchema(Schema):
    email: str


class ResetPasswordSchema(Schema):
    token: str
    new_password: str


class TokenResponse(Schema):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(Schema):
    message: str


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@router.post("/register", response={201: TokenResponse, 400: dict})
def register(request, data: RegisterSchema):
    """Register a new user"""
    if User.objects.filter(username=data.username).exists():
        return 400, {"error": "Username already exists"}
    
    if User.objects.filter(email=data.email).exists():
        return 400, {"error": "Email already exists"}
    
    # Create user - Django's set_password uses PBKDF2 by default
    # We'll use Django's password hashing which is secure
    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,  # Django will hash it securely
        first_name=data.first_name,
        last_name=data.last_name
    )
    
    token = create_access_token(user)
    return 201, {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/login", response={200: TokenResponse, 401: dict})
def login(request, data: LoginSchema):
    """Login and get JWT token"""
    user = authenticate(username=data.username, password=data.password)
    
    if user is None:
        return 401, {"error": "Invalid credentials"}
    
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/forgot-password", response={200: MessageResponse, 404: dict})
def forgot_password(request, data: ForgotPasswordSchema):
    """Send password reset email"""
    try:
        user = User.objects.get(email=data.email)
        
        # Create reset token (valid for 1 hour)
        reset_payload = {
            'user_id': user.id,
            'email': user.email,
            'type': 'password_reset',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        reset_token = jwt.encode(reset_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        
        # Send email with reset link
        reset_url = f"http://localhost:8000/auth/reset-password?token={reset_token}"
        send_mail(
            subject='Password Reset Request',
            message=f'Click the following link to reset your password: {reset_url}\n\nThis link will expire in 1 hour.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return {"message": "Password reset email sent"}
    except User.DoesNotExist:
        return 404, {"error": "User with this email does not exist"}


@router.post("/reset-password", response={200: MessageResponse, 400: dict})
def reset_password(request, data: ResetPasswordSchema):
    """Reset password using token"""
    try:
        payload = jwt.decode(
            data.token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get('type') != 'password_reset':
            return 400, {"error": "Invalid token type"}
        
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        
        # Update password using Django's set_password (uses PBKDF2)
        user.set_password(data.new_password)
        user.save()
        
        return {"message": "Password reset successfully"}
    except jwt.ExpiredSignatureError:
        return 400, {"error": "Reset token has expired"}
    except jwt.InvalidTokenError:
        return 400, {"error": "Invalid reset token"}
    except User.DoesNotExist:
        return 400, {"error": "User not found"}

