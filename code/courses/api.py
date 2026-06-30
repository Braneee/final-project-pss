"""
Courses API Endpoints - dengan Redis Caching & Rate Limiting

Public (tanpa auth):
  GET  /api/courses          - List semua course (cached Redis, rate limited 60/menit)
  GET  /api/courses/{id}     - Detail satu course (cached Redis)

Protected:
  POST   /api/courses         - Buat course baru (Instructor/Admin)
  PATCH  /api/courses/{id}    - Update course (Owner/Admin)
  DELETE /api/courses/{id}    - Hapus course (Admin only)
  POST   /api/courses/export-report - Export CSV async (Admin)
"""

import json
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from ninja import Router, Query
from ninja.errors import HttpError

from accounts.auth_bearer import AuthBearer
from accounts.permissions import is_instructor, is_admin, is_owner_or_admin
from activity_logs.logger import log_activity
from .models import Course
from .schemas import (
    CourseCreateSchema, CourseUpdateSchema, CourseFilterSchema,
    CourseOut, CourseListOut, InstructorOut, MessageOut
)

router = Router(tags=["Courses"])

# ---------------------------------------------------------------------------
# Cache key helpers
# ---------------------------------------------------------------------------

def _cache_key_list(filters) -> str:
    return f"course_list:{filters.page}:{filters.page_size}:{filters.level}:{filters.min_price}:{filters.max_price}:{filters.search}"

def _cache_key_detail(course_id: int) -> str:
    return f"course_detail:{course_id}"


def _course_to_out(course: Course) -> CourseOut:
    return CourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        price=course.price,
        level=course.level,
        is_published=course.is_published,
        instructor=InstructorOut(
            id=course.instructor.id,
            username=course.instructor.username,
            email=course.instructor.email,
        ),
        created_at=course.created_at,
    )


def _invalidate_course_cache(course_id: int = None):
    """Hapus cache course list dan detail spesifik saat ada perubahan data."""
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys("lms:course_list:*")
        if keys:
            conn.delete(*keys)
    except Exception:
        # Fallback jika redis connection tidak tersedia
        cache.clear()
    if course_id:
        cache.delete(f"course_detail:{course_id}")


# ---------------------------------------------------------------------------
# GET /api/courses  (Public, Cached, Rate Limited)
# ---------------------------------------------------------------------------

def _check_rate_limit(request) -> bool:
    """Simple rate limiter: 60 request/menit per IP menggunakan Redis."""
    ip  = request.META.get("REMOTE_ADDR", "unknown")
    key = f"rate_limit:courses_list:{ip}"
    count = cache.get(key, 0)
    if count >= 60:
        return False
    cache.set(key, count + 1, timeout=60)
    return True


@router.get("", response=CourseListOut)
def list_courses(request, filters: CourseFilterSchema = Query(CourseFilterSchema())):
    """
    List semua course yang sudah dipublish.
    - Hasil di-cache Redis selama 5 menit.
    - Rate limit: 60 request/menit per IP.
    """
    # Rate limiting
    if not _check_rate_limit(request):
        raise HttpError(429, "Terlalu banyak request. Coba lagi dalam 1 menit.")

    # Cek cache
    cache_key = _cache_key_list(filters)
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Query database
    qs = Course.objects.select_related("instructor").filter(is_published=True)

    if filters.level:
        qs = qs.filter(level=filters.level)
    if filters.min_price is not None:
        qs = qs.filter(price__gte=filters.min_price)
    if filters.max_price is not None:
        qs = qs.filter(price__lte=filters.max_price)
    if filters.search:
        qs = qs.filter(title__icontains=filters.search)

    total  = qs.count()
    offset = (filters.page - 1) * filters.page_size
    qs     = qs[offset: offset + filters.page_size]

    result = CourseListOut(
        total=total,
        page=filters.page,
        per_page=filters.page_size,
        results=[_course_to_out(c) for c in qs],
    )

    # Simpan ke cache
    cache.set(cache_key, result, timeout=settings.CACHE_TTL_COURSE_LIST)
    return result


# ---------------------------------------------------------------------------
# GET /api/courses/{id}  (Public, Cached)
# ---------------------------------------------------------------------------

@router.get("/{course_id}", response={200: CourseOut, 404: MessageOut})
def get_course(request, course_id: int):
    """Detail satu course. Hasil di-cache Redis selama 10 menit."""
    cache_key = _cache_key_detail(course_id)
    cached = cache.get(cache_key)
    if cached:
        return 200, cached

    try:
        course = Course.objects.select_related("instructor").get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"message": "Course tidak ditemukan"}

    result = _course_to_out(course)
    cache.set(cache_key, result, timeout=settings.CACHE_TTL_COURSE_DETAIL)

    # Log activity ke MongoDB
    if hasattr(request, "user") and request.user.is_authenticated:
        log_activity(
            user_id=request.user.id,
            username=request.user.username,
            action="view_course",
            resource="course",
            resource_id=course_id,
        )

    return 200, result


# ---------------------------------------------------------------------------
# POST /api/courses  (Instructor / Admin)
# ---------------------------------------------------------------------------

@router.post("", response={201: CourseOut, 403: MessageOut}, auth=AuthBearer())
@is_instructor
def create_course(request, data: CourseCreateSchema):
    """Buat course baru. Hanya Instructor dan Admin yang bisa."""
    course = Course.objects.create(
        title=data.title,
        description=data.description,
        price=data.price,
        level=data.level,
        is_published=data.is_published,
        instructor=request.user,
    )
    _invalidate_course_cache()

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="create_course",
        resource="course",
        resource_id=course.id,
        extra={"title": course.title},
    )

    return 201, _course_to_out(course)


# ---------------------------------------------------------------------------
# PATCH /api/courses/{id}  (Owner / Admin)
# ---------------------------------------------------------------------------

@router.patch("/{course_id}", response={200: CourseOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
def update_course(request, course_id: int, data: CourseUpdateSchema):
    """Update course. Hanya pemilik course (instructor) atau Admin yang bisa."""
    try:
        course = Course.objects.select_related("instructor").get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"message": "Course tidak ditemukan"}

    if not is_owner_or_admin(request.user, course.instructor_id):
        return 403, {"message": "Kamu bukan pemilik course ini"}

    if data.title        is not None: course.title        = data.title
    if data.description  is not None: course.description  = data.description
    if data.price        is not None: course.price        = data.price
    if data.level        is not None: course.level        = data.level
    if data.is_published is not None: course.is_published = data.is_published
    course.save()

    _invalidate_course_cache(course_id)

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="update_course",
        resource="course",
        resource_id=course_id,
    )

    return 200, _course_to_out(course)


# ---------------------------------------------------------------------------
# DELETE /api/courses/{id}  (Admin only)
# ---------------------------------------------------------------------------

@router.delete("/{course_id}", response={200: MessageOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_admin
def delete_course(request, course_id: int):
    """Hapus course. Hanya Admin yang bisa."""
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"message": "Course tidak ditemukan"}

    title = course.title
    course.delete()
    _invalidate_course_cache(course_id)

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="delete_course",
        resource="course",
        resource_id=course_id,
        extra={"title": title},
    )

    return 200, {"message": f"Course '{title}' berhasil dihapus"}


# ---------------------------------------------------------------------------
# POST /api/courses/export-report  (Admin - Async via Celery)
# ---------------------------------------------------------------------------

@router.post("/export-report", response={202: MessageOut, 403: MessageOut}, auth=AuthBearer())
@is_admin
def export_report(request):
    """
    Trigger export CSV semua courses secara async (Celery).
    Hasilnya bisa dilihat di Flower dashboard.
    """
    from courses.tasks import export_course_report
    task = export_course_report.delay()

    return 202, {"message": f"Export sedang diproses. Task ID: {task.id}"}


# ---------------------------------------------------------------------------
# GET /api/courses/tasks/{task_id}/status
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/status", response={200: dict, 404: MessageOut}, auth=AuthBearer())
def get_task_status(request, task_id: str):
    """
    Cek status pekerjaan asinkron Celery berdasarkan Task ID.
    """
    from celery.result import AsyncResult
    from lms.celery import app as celery_app

    res = AsyncResult(task_id, app=celery_app)
    return 200, {
        "task_id": task_id,
        "status": res.status,
        "ready": res.ready(),
        "result": str(res.result) if res.ready() else None
    }

