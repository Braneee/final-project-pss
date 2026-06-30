from django.core.management.base import BaseCommand
from lms.celery import app


class Command(BaseCommand):
    help = "Menampilkan 4 Celery task utama yang harus terdaftar"

    def handle(self, *args, **options):
        app.loader.import_default_modules()

        required_tasks = [
            "enrollments.tasks.send_enrollment_email",
            "enrollments.tasks.generate_certificate",
            "courses.tasks.update_course_statistics",
            "courses.tasks.export_course_report",
        ]

        registered = set(app.tasks.keys())

        for task_name in required_tasks:
            status = "OK" if task_name in registered else "MISSING"
            self.stdout.write(f"{status} - {task_name}")

        missing = [
            task_name
            for task_name in required_tasks
            if task_name not in registered
        ]

        if missing:
            raise SystemExit(1)