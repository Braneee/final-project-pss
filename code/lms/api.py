"""
Main API Router - Titik masuk semua endpoint Django Ninja

Swagger UI tersedia di: http://localhost:8000/api/docs
ReDoc tersedia di:      http://localhost:8000/api/redoc
"""

from ninja import NinjaAPI
from ninja.errors import ValidationError, HttpError
from django.http import JsonResponse

from accounts.api     import router as auth_router
from courses.api      import router as courses_router
from courses.quizzes_api import router as quizzes_router
from enrollments.api  import router as enrollments_router
from activity_logs.api import router as logs_router

# Inisialisasi NinjaAPI
api = NinjaAPI(
    title="Simple LMS API",
    version="2.0.0",
    description="""
## 📚 Simple LMS REST API

API untuk sistem Learning Management System sederhana.

### Fitur:
- **Auth**: Register, Login, JWT Token, Refresh Token
- **Courses**: CRUD kursus dengan Redis caching & rate limiting (60 req/menit)
- **Enrollments**: Pendaftaran kursus, tracking progres, Celery async tasks
- **Activity Logs**: MongoDB-based activity & analytics logs (Admin only)

### Cara Autentikasi:
1. Register atau Login untuk mendapatkan `access_token`
2. Klik tombol **Authorize** di atas
3. Masukkan: `Bearer <access_token>`

### Tech Stack (Baru):
- 🔴 **Redis**: Caching course list & detail
- 🍃 **MongoDB**: Activity logs & learning analytics
- 🌿 **Celery + RabbitMQ**: Async email, certificate generation
- 📊 **Flower**: Celery monitoring di port 5555
""",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Daftarkan semua router dengan prefix-nya
api.add_router("/auth",        auth_router)
api.add_router("/courses",     courses_router)
api.add_router("/quizzes",     quizzes_router)
api.add_router("/enrollments", enrollments_router)
api.add_router("/logs",        logs_router)


# =============================================================================
# Global Error Handlers
# =============================================================================

@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    """Format error validasi Pydantic menjadi response yang rapi."""
    return JsonResponse(
        {"message": "Data tidak valid", "errors": exc.errors},
        status=422,
    )
