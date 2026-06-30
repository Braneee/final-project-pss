"""
Enrollments API Endpoints - dengan Celery Tasks & Activity Logging

POST /api/enrollments                    - Daftar ke course (Student) → trigger email task
GET  /api/enrollments/my-courses         - Lihat course yang sudah didaftar
POST /api/enrollments/{id}/progress      - Tandai lesson selesai → trigger certificate task
"""

from datetime import datetime, timezone
from ninja import Router
from ninja.errors import HttpError

from accounts.auth_bearer import AuthBearer
from accounts.permissions import is_student
from activity_logs.logger import log_activity, log_learning_analytics
from courses.models import Course, CourseContent
from django.http import FileResponse
from .models import Enrollment, LessonProgress, Certificate
from .schemas import (
    EnrollSchema, ProgressSchema,
    EnrollmentOut, CourseSimpleOut, ProgressOut, MessageOut, CertificateOut
)

router = Router(tags=["Enrollments"])


def _enrollment_to_out(e: Enrollment) -> EnrollmentOut:
    return EnrollmentOut(
        id=e.id,
        course=CourseSimpleOut(
            id=e.course.id,
            title=e.course.title,
            level=e.course.level,
            price=e.course.price,
        ),
        enrolled_at=e.enrolled_at,
        is_active=e.is_active,
    )


# ---------------------------------------------------------------------------
# POST /api/enrollments  (Student)
# ---------------------------------------------------------------------------

@router.post("", response={201: EnrollmentOut, 400: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_student
def enroll(request, data: EnrollSchema):
    """
    Daftar ke sebuah course.
    - Setelah enroll berhasil, secara async mengirim email konfirmasi via Celery.
    - Aktivitas dicatat ke MongoDB.
    """
    try:
        course = Course.objects.get(id=data.course_id, is_published=True)
    except Course.DoesNotExist:
        return 404, {"message": "Course tidak ditemukan atau belum dipublish"}

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return 400, {"message": "Kamu sudah terdaftar di course ini"}

    enrollment = Enrollment.objects.create(student=request.user, course=course)

    # Kirim email async via Celery
    from enrollments.tasks import send_enrollment_email
    send_enrollment_email.delay(request.user.id, course.id)

    # Log activity ke MongoDB
    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="enroll",
        resource="course",
        resource_id=course.id,
        extra={"course_title": course.title},
    )

    return 201, _enrollment_to_out(enrollment)


# ---------------------------------------------------------------------------
# GET /api/enrollments/my-courses  (Student)
# ---------------------------------------------------------------------------

@router.get("/my-courses", response=list[EnrollmentOut], auth=AuthBearer())
@is_student
def my_courses(request):
    """Lihat semua course yang sudah kamu daftar."""
    enrollments = (
        Enrollment.objects
        .select_related("course")
        .filter(student=request.user, is_active=True)
    )
    return [_enrollment_to_out(e) for e in enrollments]


# ---------------------------------------------------------------------------
# POST /api/enrollments/{enrollment_id}/progress  (Student)
# ---------------------------------------------------------------------------

@router.post(
    "/{enrollment_id}/progress",
    response={200: ProgressOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AuthBearer()
)
@is_student
def mark_progress(request, enrollment_id: int, data: ProgressSchema):
    """
    Tandai sebuah lesson/konten sebagai selesai atau belum selesai.
    Jika semua lesson selesai, secara async generate sertifikat via Celery.
    """
    try:
        enrollment = Enrollment.objects.select_related("course").get(
            id=enrollment_id,
            student=request.user
        )
    except Enrollment.DoesNotExist:
        return 404, {"message": "Enrollment tidak ditemukan"}

    try:
        content = CourseContent.objects.get(id=data.content_id, course=enrollment.course)
    except CourseContent.DoesNotExist:
        return 404, {"message": "Konten tidak ditemukan di course ini"}

    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        content=content,
    )
    progress.is_complete  = data.is_complete
    progress.completed_at = datetime.now(timezone.utc) if data.is_complete else None
    progress.save()

    # Log analytics ke MongoDB
    if data.is_complete:
        log_learning_analytics(
            user_id=request.user.id,
            course_id=enrollment.course.id,
            event="lesson_completed",
            data={"content_id": content.id, "content_title": content.title},
        )

        # Cek apakah semua lesson selesai → generate sertifikat async
        total     = enrollment.course.contents.count()
        completed = LessonProgress.objects.filter(enrollment=enrollment, is_complete=True).count()
        if total > 0 and completed >= total:
            from enrollments.tasks import generate_certificate
            generate_certificate.delay(request.user.id, enrollment.course.id)

            log_learning_analytics(
                user_id=request.user.id,
                course_id=enrollment.course.id,
                event="course_completed",
            )

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="complete_lesson" if data.is_complete else "uncomplete_lesson",
        resource="lesson",
        resource_id=content.id,
        extra={"enrollment_id": enrollment_id},
    )

    return 200, ProgressOut(
        content_id=content.id,
        content_title=content.title,
        is_complete=progress.is_complete,
        completed_at=progress.completed_at,
    )


# ---------------------------------------------------------------------------
# GET /api/enrollments/my-certificates (Student)
# ---------------------------------------------------------------------------
@router.get("/my-certificates", response=list[CertificateOut], auth=AuthBearer())
@is_student
def my_certificates(request):
    """Lihat semua sertifikat yang telah diperoleh."""
    certs = Certificate.objects.select_related("course").filter(student=request.user)
    results = []
    for c in certs:
        pdf_url = request.build_absolute_uri(c.pdf_file.url) if c.pdf_file else None
        results.append(CertificateOut(
            id=c.id,
            course_title=c.course.title,
            certificate_code=c.certificate_code,
            pdf_url=pdf_url,
            issued_at=c.issued_at,
        ))
    return results


# ---------------------------------------------------------------------------
# GET /api/enrollments/certificates/verify/{certificate_code} (Public)
# ---------------------------------------------------------------------------
@router.get("/certificates/verify/{certificate_code}", response={200: dict, 404: MessageOut})
def verify_certificate(request, certificate_code: str):
    """
    Verifikasi keabsahan sertifikat secara publik menggunakan kode sertifikat.
    Tidak memerlukan autentikasi.
    """
    try:
        cert = Certificate.objects.select_related("student", "course").get(certificate_code=certificate_code)
    except Certificate.DoesNotExist:
        return 404, {"message": "Sertifikat tidak valid atau tidak ditemukan"}

    student_name = cert.student.get_full_name() or cert.student.username
    return 200, {
        "valid": True,
        "certificate_code": cert.certificate_code,
        "student_name": student_name,
        "course_title": cert.course.title,
        "issued_at": cert.issued_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /api/enrollments/certificates/{certificate_id}/download (Authenticated)
# ---------------------------------------------------------------------------
@router.get("/certificates/{certificate_id}/download", auth=AuthBearer())
def download_certificate(request, certificate_id: int):
    """Mengunduh file PDF sertifikat jika yang meminta adalah pemilik atau admin."""
    from accounts.permissions import is_owner_or_admin
    try:
        cert = Certificate.objects.get(id=certificate_id)
    except Certificate.DoesNotExist:
        raise HttpError(404, "Sertifikat tidak ditemukan")

    if not is_owner_or_admin(request.user, cert.student_id):
        raise HttpError(403, "Akses ditolak: Kamu bukan pemilik sertifikat ini")

    if not cert.pdf_file:
        raise HttpError(404, "File PDF sertifikat belum di-generate")

    return FileResponse(cert.pdf_file.open(), content_type="application/pdf", filename=f"sertifikat_{cert.certificate_code}.pdf")

