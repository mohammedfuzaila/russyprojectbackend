from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

urlpatterns = [
    path('', lambda r: HttpResponse('<div style="font-family:sans-serif;text-align:center;padding:50px;"><h1>🌶️ Russy API is Running</h1><p>Your backend is live and healthy.</p></div>')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
