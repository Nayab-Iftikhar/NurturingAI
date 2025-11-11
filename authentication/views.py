from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import bcrypt
import jwt
from datetime import datetime, timedelta


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False


def signup_view(request):
    """Signup page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'auth/signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'auth/signup.html')
        
        # Create user - Django's create_user will hash the password securely
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,  # Django will hash it using PBKDF2
            first_name=first_name,
            last_name=last_name
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'auth/signup.html')


def login_view(request):
    """Login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            django_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'auth/login.html')


def forgot_password_view(request):
    """Forgot password page"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Create reset token
            reset_payload = {
                'user_id': user.id,
                'email': user.email,
                'type': 'password_reset',
                'exp': datetime.utcnow() + timedelta(hours=1),
                'iat': datetime.utcnow()
            }
            reset_token = jwt.encode(reset_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            
            # Send email
            reset_url = f"{request.scheme}://{request.get_host()}/auth/reset-password?token={reset_token}"
            send_mail(
                subject='Password Reset Request',
                message=f'Click the following link to reset your password: {reset_url}\n\nThis link will expire in 1 hour.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            messages.success(request, 'Password reset email sent! Check your inbox.')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address')
    
    return render(request, 'auth/forgot_password.html')


def reset_password_view(request):
    """Reset password page"""
    token = request.GET.get('token')
    
    if not token:
        messages.error(request, 'Invalid reset link')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'auth/reset_password.html', {'token': token})
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get('type') != 'password_reset':
                messages.error(request, 'Invalid reset token')
                return redirect('forgot_password')
            
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            # Update password using Django's set_password
            user.set_password(new_password)
            user.save()
            
            messages.success(request, 'Password reset successfully! Please login.')
            return redirect('login')
        except jwt.ExpiredSignatureError:
            messages.error(request, 'Reset link has expired. Please request a new one.')
            return redirect('forgot_password')
        except jwt.InvalidTokenError:
            messages.error(request, 'Invalid reset link')
            return redirect('forgot_password')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('forgot_password')
    
    return render(request, 'auth/reset_password.html', {'token': token})


def logout_view(request):
    """Logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')
