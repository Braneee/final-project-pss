"""
RBAC - Role-Based Access Control

Menyediakan decorator untuk membatasi akses endpoint berdasarkan role user.

Penggunaan:
    from accounts.permissions import is_instructor, is_admin, is_student

    @router.post("/courses", auth=AuthBearer())
    @is_instructor
    def create_course(request, ...):
        ...

Role hierarchy:
    admin      → bisa akses semua
    instructor → bisa manage course miliknya
    student    → hanya bisa enroll & lihat course
"""

from functools import wraps
from ninja.errors import HttpError


def _get_role(request) -> str:
    """Ambil role dari user yang sudah login."""
    profile = getattr(request.user, 'profile', None)
    return profile.role if profile else 'student'


def is_admin(func):
    """Hanya admin yang boleh akses endpoint ini."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        role = _get_role(request)
        if role != 'admin':
            raise HttpError(403, "Akses ditolak: hanya Admin yang diizinkan")
        return func(request, *args, **kwargs)
    return wrapper


def is_instructor(func):
    """Instructor dan Admin yang boleh akses endpoint ini."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        role = _get_role(request)
        if role not in ('instructor', 'admin'):
            raise HttpError(403, "Akses ditolak: hanya Instructor atau Admin yang diizinkan")
        return func(request, *args, **kwargs)
    return wrapper


def is_student(func):
    """Semua role boleh akses (student, instructor, admin)."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Semua authenticated user boleh akses
        return func(request, *args, **kwargs)
    return wrapper


def is_owner_or_admin(user, obj_owner_id: int):
    """
    Helper untuk cek apakah user adalah pemilik object atau admin.
    Digunakan di dalam view, bukan sebagai decorator.

    Contoh:
        if not is_owner_or_admin(request.user, course.instructor_id):
            raise HttpError(403, "Bukan pemilik course ini")
    """
    profile = getattr(user, 'profile', None)
    role    = profile.role if profile else 'student'
    return role == 'admin' or user.id == obj_owner_id
