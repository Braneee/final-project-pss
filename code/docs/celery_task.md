# Celery Tasks Documentation

Project ini memiliki minimal 4 Celery task sesuai ketentuan.

## Daftar Task

1. `enrollments.tasks.send_enrollment_email`
   - Jenis: asynchronous task.
   - Fungsi: mengirim email saat student enroll ke course.

2. `enrollments.tasks.generate_certificate`
   - Jenis: asynchronous task.
   - Fungsi: generate certificate saat student menyelesaikan course.

3. `courses.tasks.update_course_statistics`
   - Jenis: scheduled task.
   - Fungsi: update statistik course secara terjadwal menggunakan Celery Beat.

4. `courses.tasks.export_course_report`
   - Jenis: asynchronous task.
   - Fungsi: generate laporan course dalam format CSV.

## Cara Mengecek Task

Jalankan semua service Docker:

```bash
docker compose up -d --build