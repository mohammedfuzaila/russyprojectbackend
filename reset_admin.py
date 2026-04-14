import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import User, Cart

try:
    user = User.objects.get(email='admin@russymasala.com')
    print("Found existing user:", user.email)
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.set_password('admin123')
    user.save()
    
    # Ensure they have a cart
    Cart.objects.get_or_create(user=user)
    
    print("User credentials and permissions fully reset successfully.")
except User.DoesNotExist:
    print("User does not exist. Creating new superuser...")
    user = User.objects.create_superuser('admin@russymasala.com', 'Admin User', 'admin123')
    Cart.objects.get_or_create(user=user)
    print("Superuser created successfully.")
