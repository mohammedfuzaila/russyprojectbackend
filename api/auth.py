"""
JWT Authentication helpers — pure Django (no DRF).
Generates and validates HS256 JWTs using PyJWT.
"""
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.http import JsonResponse
from api.models import User
import functools


def generate_token(user):
    """Create a signed JWT for the given user."""
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token):
    """Decode a JWT. Returns the payload dict or raises jwt exceptions."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def get_user_from_request(request):
    """Extract and validate the Bearer token, return User or None."""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = decode_token(token)
        return User.objects.get(id=payload['user_id'], is_active=True)
    except Exception:
        return None


def jwt_required(view_func):
    """Decorator: protects a view — returns 401 if no valid token."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_user_from_request(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        request.current_user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator: protects a view — returns 403 if no valid token or not an admin."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_user_from_request(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        if not user.is_staff and not user.is_superuser:
            return JsonResponse({'error': 'Admin privileges required'}, status=403)
        request.current_user = user
        return view_func(request, *args, **kwargs)
    return wrapper

