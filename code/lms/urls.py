"""
URL Configuration - Simple LMS

Routes:
  /admin/    → Django Admin panel
  /silk/     → Django Silk profiling dashboard
  /api/      → Django Ninja REST API (semua endpoint)
  /api/docs  → Swagger UI (auto-generated)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .api import api   # Django Ninja instance
from courses.views import demo_view, login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('silk/',  include('silk.urls', namespace='silk')),
    path('api/',   api.urls),   # Semua endpoint REST API + Swagger
    path('login/', login_view, name='demo_login'), # Halaman login terpisah
    path('',       demo_view, name='demo_frontend'), # UI demo kuis & sertifikat
]

# Serve media files di development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
