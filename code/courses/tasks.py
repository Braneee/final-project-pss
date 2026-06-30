import os
import csv
import time
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="courses.tasks.update_course_statistics")
def update_course_statistics():
    """
    Scheduled task untuk update statistik course.
    Task ini dijalankan otomatis oleh Celery Beat setiap hari.
    """
    from courses.models import Course
    from enrollments.models import Enrollment

    updated = 0

    for course in Course.objects.all():
        enrollment_count = Enrollment.objects.filter(
            course=course,
            is_active=True
        ).count()

        logger.info(
            f"[Statistics] Course '{course.title}' id={course.id}: "
            f"{enrollment_count} enrollment aktif"
        )

        updated += 1

    logger.info(f"[Statistics] Selesai update {updated} course pada {timezone.now()}")

    return {
        "updated_courses": updated,
        "timestamp": str(timezone.now()),
    }


@shared_task(name="courses.tasks.export_course_report")
def export_course_report(course_id: int = None):
    """
    Async task untuk generate laporan CSV enrollment course.
    File laporan disimpan ke folder media/reports.
    """
    from enrollments.models import Enrollment

    report_dir = os.path.join(settings.MEDIA_ROOT, "reports")
    os.makedirs(report_dir, exist_ok=True)

    timestamp = int(time.time())
    label = course_id if course_id else "all"
    filename = f"report_course_{label}_{timestamp}.csv"
    filepath = os.path.join(report_dir, filename)

    queryset = Enrollment.objects.select_related(
        "student",
        "course"
    ).filter(is_active=True)

    if course_id:
        queryset = queryset.filter(course_id=course_id)

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "No",
            "Username",
            "Email",
            "Course",
            "Enrollment Date",
        ])

        for index, enrollment in enumerate(queryset, start=1):
            student = enrollment.student
            course = enrollment.course

            writer.writerow([
                index,
                student.username,
                student.email,
                course.title,
                enrollment.enrolled_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    row_count = queryset.count()

    logger.info(f"[Export] Report berhasil dibuat: {filepath}")

    return {
        "status": "generated",
        "file": filepath,
        "filename": filename,
        "rows": row_count,
    }