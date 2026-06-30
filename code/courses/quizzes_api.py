from django.shortcuts import get_object_or_404
from django.db.models import Sum
from ninja import Router
from ninja.errors import HttpError
from typing import List

from accounts.auth_bearer import AuthBearer
from accounts.permissions import is_instructor, is_student, is_owner_or_admin
from activity_logs.logger import log_activity, log_learning_analytics
from courses.models import Course, CourseContent, Quiz, Question, Choice
from enrollments.models import Enrollment, QuizAttempt, LessonProgress
from courses.schemas import (
    QuizCreateSchema, QuizUpdateSchema, QuestionCreateSchema, QuestionUpdateSchema,
    QuizOut, QuizInstructorOut, QuestionInstructorOut, QuizSubmitSchema,
    QuizSubmitResultOut, MessageOut
)

router = Router(tags=["Quizzes"])


# ---------------------------------------------------------------------------
# Helper Serializers to avoid Pydantic lazy relation loading issues
# ---------------------------------------------------------------------------
def _choice_to_out(c: Choice, include_correct: bool = False) -> dict:
    res = {
        "id": c.id,
        "text": c.text,
    }
    if include_correct:
        res["is_correct"] = c.is_correct
    return res

def _question_to_out(q: Question, include_correct: bool = False) -> dict:
    return {
        "id": q.id,
        "text": q.text,
        "weight": q.weight,
        "choices": [_choice_to_out(c, include_correct) for c in q.choices.all()]
    }

def _quiz_to_out(quiz: Quiz, include_correct: bool = False) -> dict:
    return {
        "id": quiz.id,
        "course_id": quiz.course_id,
        "lesson_id": quiz.lesson_id,
        "title": quiz.title,
        "description": quiz.description,
        "passing_grade": quiz.passing_grade,
        "attempt_limit": quiz.attempt_limit,
        "questions": [_question_to_out(q, include_correct) for q in quiz.questions.all()]
    }



# ---------------------------------------------------------------------------
# POST /api/quizzes (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.post("", response={201: QuizInstructorOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def create_quiz(request, data: QuizCreateSchema):
    """
    Buat kuis baru untuk sebuah course (dan opsional lesson/materi).
    Hanya Instructor pemilik course atau Admin yang diizinkan.
    """
    course = get_object_or_404(Course, id=data.course_id)
    
    if not is_owner_or_admin(request.user, course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    lesson = None
    if data.lesson_id:
        lesson = get_object_or_404(CourseContent, id=data.lesson_id, course=course)

    quiz = Quiz.objects.create(
        course=course,
        lesson=lesson,
        title=data.title,
        description=data.description or "",
        passing_grade=data.passing_grade,
        attempt_limit=data.attempt_limit,
    )

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="create_quiz",
        resource="quiz",
        resource_id=quiz.id,
        extra={"title": quiz.title, "course_id": course.id},
    )

    return 201, _quiz_to_out(quiz, include_correct=True)


# ---------------------------------------------------------------------------
# POST /api/quizzes/{quiz_id}/questions (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.post("/{quiz_id}/questions", response={201: QuestionInstructorOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def add_question(request, quiz_id: int, data: QuestionCreateSchema):
    """
    Tambahkan pertanyaan dan pilihan jawabannya ke kuis.
    Hanya Instructor pemilik kuis/course atau Admin yang diizinkan.
    """
    quiz = get_object_or_404(Quiz.objects.select_related("course"), id=quiz_id)
    
    if not is_owner_or_admin(request.user, quiz.course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    # Buat pertanyaan
    question = Question.objects.create(
        quiz=quiz,
        text=data.text,
        weight=data.weight,
    )

    # Buat pilihan jawaban
    for c in data.choices:
        Choice.objects.create(
            question=question,
            text=c.text,
            is_correct=c.is_correct,
        )

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="add_question",
        resource="question",
        resource_id=question.id,
        extra={"quiz_id": quiz.id},
    )

    return 201, _question_to_out(question, include_correct=True)


# ---------------------------------------------------------------------------
# GET /api/quizzes/{quiz_id} (Student / Instructor / Admin)
# ---------------------------------------------------------------------------
@router.get("/{quiz_id}", response={200: QuizOut, 203: QuizInstructorOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
def get_quiz(request, quiz_id: int):
    """
    Ambil detail kuis beserta pertanyaannya.
    - Siswa: melihat pilihan jawaban tanpa kunci jawaban (`is_correct` disembunyikan).
    - Instruktur/Admin: melihat detail penuh beserta kunci jawabannya.
    """
    quiz = get_object_or_404(Quiz.objects.select_related("course"), id=quiz_id)
    
    # Cek permission
    role = getattr(request.user.profile, 'role', 'student') if hasattr(request.user, 'profile') else 'student'
    
    if role not in ('instructor', 'admin'):
        # Pastikan student sudah enroll ke course terkait
        if not Enrollment.objects.filter(student=request.user, course=quiz.course, is_active=True).exists():
            return 403, {"message": "Akses ditolak: Kamu harus terdaftar (enrolled) di kelas ini terlebih dahulu"}
        
        # Kembalikan response Siswa (kunci jawaban disembunyikan)
        return 200, _quiz_to_out(quiz, include_correct=False)
    else:
        # Instruktur / Admin
        if not is_owner_or_admin(request.user, quiz.course.instructor_id):
            return 403, {"message": "Akses ditolak: Kamu bukan pemilik kuis ini"}
        
        # Kembalikan response Instruktur (kunci jawaban terlihat)
        return 203, _quiz_to_out(quiz, include_correct=True)


# ---------------------------------------------------------------------------
# POST /api/quizzes/{quiz_id}/submit (Student)
# ---------------------------------------------------------------------------
@router.post("/{quiz_id}/submit", response={200: QuizSubmitResultOut, 400: MessageOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_student
def submit_quiz(request, quiz_id: int, data: QuizSubmitSchema):
    """
    Kirimkan jawaban kuis untuk dinilai secara otomatis.
    - Sistem akan memeriksa batas pengerjaan kuis.
    - Sistem menghitung total bobot soal dan persentase nilai akhir.
    - Jika persentase nilai >= passing grade, attempt ditandai Lulus.
    - Jika siswa lulus kuis & telah menyelesaikan semua lesson, sertifikat di-generate secara async via Celery.
    """
    quiz = get_object_or_404(Quiz.objects.select_related("course"), id=quiz_id)
    
    # Pastikan student sudah enroll
    enrollment = Enrollment.objects.filter(student=request.user, course=quiz.course, is_active=True).first()
    if not enrollment:
        return 403, {"message": "Akses ditolak: Kamu harus terdaftar (enrolled) di kelas ini terlebih dahulu"}

    # Cek attempt limit
    attempts_count = QuizAttempt.objects.filter(student=request.user, quiz=quiz).count()
    if attempts_count >= quiz.attempt_limit:
        return 400, {"message": f"Batas pengerjaan kuis telah habis (Maksimal {quiz.attempt_limit} kali)"}

    # Ambil semua pertanyaan di kuis ini
    questions = quiz.questions.all().prefetch_related("choices")
    if not questions.exists():
        return 400, {"message": "Kuis ini belum memiliki pertanyaan"}

    # Map answers yang dikirim siswa
    student_answers = {ans.question_id: ans.choice_id for ans in data.answers}

    total_weight = 0
    earned_score = 0

    for q in questions:
        total_weight += q.weight
        student_choice_id = student_answers.get(q.id)
        if student_choice_id:
            # Temukan pilihan jawaban
            correct_choice = next((c for c in q.choices.all() if c.is_correct), None)
            if correct_choice and correct_choice.id == student_choice_id:
                earned_score += q.weight

    # Hitung nilai akhir skala 0-100
    final_score = int((earned_score / total_weight) * 100) if total_weight > 0 else 0
    is_passed = final_score >= quiz.passing_grade

    # Catat attempt
    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz,
        score=final_score,
        is_passed=is_passed,
        attempt_number=attempts_count + 1
    )

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="submit_quiz",
        resource="quiz",
        resource_id=quiz.id,
        extra={"attempt_id": attempt.id, "score": final_score, "is_passed": is_passed},
    )

    log_learning_analytics(
        user_id=request.user.id,
        course_id=quiz.course.id,
        event="quiz_submitted",
        data={"quiz_id": quiz.id, "score": final_score, "is_passed": is_passed},
    )

    message = "Selamat! Anda lulus kuis ini." if is_passed else "Maaf, nilai Anda belum memenuhi batas kelulusan."

    # Cek apakah siswa berhak mendapatkan sertifikat
    # Syarat kelulusan Course:
    # 1. Semua lesson selesai (LessonProgress)
    # 2. Semua kuis di course lulus (atau minimal lulus kuis ini jika ini kuis satu-satunya)
    if is_passed:
        # Cek apakah masih ada kuis di course ini yang belum lulus
        all_quizzes_ids = quiz.course.quizzes.values_list("id", flat=True)
        passed_quizzes_count = QuizAttempt.objects.filter(
            student=request.user,
            quiz_id__in=all_quizzes_ids,
            is_passed=True
        ).values("quiz_id").distinct().count()

        total_quizzes_count = len(all_quizzes_ids)

        total_lessons = quiz.course.contents.count()
        completed_lessons = LessonProgress.objects.filter(
            enrollment=enrollment,
            is_complete=True
        ).count()

        # Jika semua kuis lulus dan semua lesson selesai
        if passed_quizzes_count >= total_quizzes_count and completed_lessons >= total_lessons:
            # Cek jika sertifikat sudah pernah dibuat untuk mencegah duplikasi
            from enrollments.models import Certificate
            if not Certificate.objects.filter(student=request.user, course=quiz.course).exists():
                from enrollments.tasks import generate_certificate
                generate_certificate.delay(request.user.id, quiz.course.id)
                message += " Selamat! Anda telah menyelesaikan seluruh mata kuliah ini dan sertifikat Anda sedang diterbitkan."

                log_learning_analytics(
                    user_id=request.user.id,
                    course_id=quiz.course.id,
                    event="course_completed",
                )

    return 200, QuizSubmitResultOut(
        score=final_score,
        passing_grade=quiz.passing_grade,
        is_passed=is_passed,
        attempt_number=attempt.attempt_number,
        attempt_limit=quiz.attempt_limit,
        message=message,
    )


# ---------------------------------------------------------------------------
# PATCH /api/quizzes/{quiz_id} (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.patch("/{quiz_id}", response={200: QuizInstructorOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def update_quiz(request, quiz_id: int, data: QuizUpdateSchema):
    """Update detail kuis. Hanya Instructor pemilik course atau Admin."""
    quiz = get_object_or_404(Quiz.objects.select_related("course"), id=quiz_id)
    if not is_owner_or_admin(request.user, quiz.course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    if data.title is not None:
        quiz.title = data.title
    if data.description is not None:
        quiz.description = data.description
    if data.passing_grade is not None:
        quiz.passing_grade = data.passing_grade
    if data.attempt_limit is not None:
        quiz.attempt_limit = data.attempt_limit
    if data.lesson_id is not None:
        if data.lesson_id == 0:
            quiz.lesson = None
        else:
            quiz.lesson = get_object_or_404(CourseContent, id=data.lesson_id, course=quiz.course)
    
    quiz.save()

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="update_quiz",
        resource="quiz",
        resource_id=quiz.id,
    )

    return 200, _quiz_to_out(quiz, include_correct=True)


# ---------------------------------------------------------------------------
# DELETE /api/quizzes/{quiz_id} (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.delete("/{quiz_id}", response={200: MessageOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def delete_quiz(request, quiz_id: int):
    """Hapus kuis. Hanya Instructor pemilik course atau Admin."""
    quiz = get_object_or_404(Quiz.objects.select_related("course"), id=quiz_id)
    if not is_owner_or_admin(request.user, quiz.course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    title = quiz.title
    quiz.delete()

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="delete_quiz",
        resource="quiz",
        resource_id=quiz_id,
        extra={"title": title},
    )

    return 200, {"message": f"Kuis '{title}' berhasil dihapus"}


# ---------------------------------------------------------------------------
# PATCH /api/quizzes/questions/{question_id} (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.patch("/questions/{question_id}", response={200: QuestionInstructorOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def update_question(request, question_id: int, data: QuestionUpdateSchema):
    """Update teks atau bobot pertanyaan. Hanya Instructor pemilik course atau Admin."""
    question = get_object_or_404(Question.objects.select_related("quiz__course"), id=question_id)
    if not is_owner_or_admin(request.user, question.quiz.course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    if data.text is not None:
        question.text = data.text
    if data.weight is not None:
        question.weight = data.weight
    question.save()

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="update_question",
        resource="question",
        resource_id=question.id,
    )

    return 200, _question_to_out(question, include_correct=True)


# ---------------------------------------------------------------------------
# DELETE /api/quizzes/questions/{question_id} (Instructor / Admin)
# ---------------------------------------------------------------------------
@router.delete("/questions/{question_id}", response={200: MessageOut, 403: MessageOut, 404: MessageOut}, auth=AuthBearer())
@is_instructor
def delete_question(request, question_id: int):
    """Hapus pertanyaan dari kuis. Hanya Instructor pemilik course atau Admin."""
    question = get_object_or_404(Question.objects.select_related("quiz__course"), id=question_id)
    if not is_owner_or_admin(request.user, question.quiz.course.instructor_id):
        return 403, {"message": "Akses ditolak: Kamu bukan pemilik course ini"}

    question.delete()

    log_activity(
        user_id=request.user.id,
        username=request.user.username,
        action="delete_question",
        resource="question",
        resource_id=question_id,
    )

    return 200, {"message": "Pertanyaan berhasil dihapus"}

