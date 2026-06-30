import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import UserProfile
from accounts.jwt_helper import create_access_token
from courses.models import Course, CourseContent, Quiz, Question, Choice
from enrollments.models import Enrollment, LessonProgress, QuizAttempt, Certificate

class LMSQuizTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.admin = User.objects.create_user(username="admin", email="admin@lms.com", password="password")
        UserProfile.objects.create(user=self.admin, role="admin")
        
        self.instructor = User.objects.create_user(username="instructor", email="inst@lms.com", password="password")
        UserProfile.objects.create(user=self.instructor, role="instructor")
        
        self.student = User.objects.create_user(username="student", email="std@lms.com", password="password")
        UserProfile.objects.create(user=self.student, role="student")
        
        self.other_instructor = User.objects.create_user(username="other_inst", email="other@lms.com", password="password")
        UserProfile.objects.create(user=self.other_instructor, role="instructor")

        # Create tokens
        self.admin_token = create_access_token(self.admin.id, self.admin.username, "admin")
        self.instructor_token = create_access_token(self.instructor.id, self.instructor.username, "instructor")
        self.student_token = create_access_token(self.student.id, self.student.username, "student")
        self.other_token = create_access_token(self.other_instructor.id, self.other_instructor.username, "instructor")

        # Create Course owned by self.instructor
        self.course = Course.objects.create(
            title="Python Advanced",
            description="Advanced Python course",
            price=150000,
            level="advanced",
            is_published=True,
            instructor=self.instructor
        )
        
        # Create Course content (lessons)
        self.lesson1 = CourseContent.objects.create(
            title="Decorators",
            description="Python Decorators",
            order=1,
            course=self.course
        )
        self.lesson2 = CourseContent.objects.create(
            title="Generators",
            description="Python Generators",
            order=2,
            course=self.course
        )

    def test_create_quiz(self):
        # 1. Instructor owner should be able to create quiz
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.instructor_token}"}
        payload = {
            "course_id": self.course.id,
            "title": "Quiz Python Advanced",
            "description": "Quiz untuk course Python",
            "passing_grade": 70,
            "attempt_limit": 3
        }
        response = self.client.post(
            "/api/quizzes",
            data=json.dumps(payload),
            content_type="application/json",
            **headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Quiz Python Advanced")
        self.assertEqual(data["course_id"], self.course.id)

        # 2. Other instructor should NOT be able to create quiz (403)
        other_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.other_token}"}
        response = self.client.post(
            "/api/quizzes",
            data=json.dumps(payload),
            content_type="application/json",
            **other_headers
        )
        self.assertEqual(response.status_code, 403)

        # 3. Student should NOT be able to create quiz (403)
        student_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        response = self.client.post(
            "/api/quizzes",
            data=json.dumps(payload),
            content_type="application/json",
            **student_headers
        )
        self.assertEqual(response.status_code, 403)

    def test_add_question_and_choices(self):
        # Setup Quiz first
        quiz = Quiz.objects.create(
            course=self.course,
            title="Quiz decorators",
            passing_grade=70,
            attempt_limit=3
        )
        
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.instructor_token}"}
        payload = {
            "text": "Apa output dari decorator?",
            "weight": 20,
            "choices": [
                {"text": "Mengembalikan fungsi baru", "is_correct": True},
                {"text": "Error", "is_correct": False},
                {"text": "None", "is_correct": False}
            ]
        }
        
        response = self.client.post(
            f"/api/quizzes/{quiz.id}/questions",
            data=json.dumps(payload),
            content_type="application/json",
            **headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["text"], "Apa output dari decorator?")
        self.assertEqual(len(data["choices"]), 3)
        
        # Verify correctness in DB
        question = Question.objects.get(id=data["id"])
        self.assertEqual(question.choices.filter(is_correct=True).count(), 1)

    def test_get_quiz_visibility(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title="Quiz 1",
            passing_grade=70,
            attempt_limit=3
        )
        q1 = Question.objects.create(quiz=quiz, text="Q1", weight=10)
        Choice.objects.create(question=q1, text="True Ans", is_correct=True)
        Choice.objects.create(question=q1, text="False Ans", is_correct=False)

        # 1. Non-enrolled student should get 403
        student_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        response = self.client.get(f"/api/quizzes/{quiz.id}", **student_headers)
        self.assertEqual(response.status_code, 403)

        # Enroll student
        Enrollment.objects.create(student=self.student, course=self.course)

        # 2. Enrolled student should be able to get quiz, but is_correct must NOT be in choices
        response = self.client.get(f"/api/quizzes/{quiz.id}", **student_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Quiz 1")
        self.assertNotIn("is_correct", data["questions"][0]["choices"][0])

        # 3. Instructor owner should get 203 (QuizInstructorOut) and can see is_correct
        inst_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.instructor_token}"}
        response = self.client.get(f"/api/quizzes/{quiz.id}", **inst_headers)
        self.assertEqual(response.status_code, 203)
        data = response.json()
        self.assertIn("is_correct", data["questions"][0]["choices"][0])
        self.assertTrue(data["questions"][0]["choices"][0]["is_correct"] or data["questions"][0]["choices"][1]["is_correct"])

    def test_submit_quiz_and_scoring(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title="Quiz 1",
            passing_grade=70,
            attempt_limit=2
        )
        q1 = Question.objects.create(quiz=quiz, text="Q1", weight=60)
        c1_correct = Choice.objects.create(question=q1, text="Correct 1", is_correct=True)
        c1_wrong = Choice.objects.create(question=q1, text="Wrong 1", is_correct=False)
        
        q2 = Question.objects.create(quiz=quiz, text="Q2", weight=40)
        c2_correct = Choice.objects.create(question=q2, text="Correct 2", is_correct=True)
        c2_wrong = Choice.objects.create(question=q2, text="Wrong 2", is_correct=False)

        # Enroll student
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)

        student_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        
        # 1. First Attempt - Failed (Score 60%)
        payload1 = {
            "answers": [
                {"question_id": q1.id, "choice_id": c1_correct.id},
                {"question_id": q2.id, "choice_id": c2_wrong.id}
            ]
        }
        response = self.client.post(
            f"/api/quizzes/{quiz.id}/submit",
            data=json.dumps(payload1),
            content_type="application/json",
            **student_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["score"], 60)
        self.assertFalse(data["is_passed"])
        self.assertEqual(data["attempt_number"], 1)

        # 2. Second Attempt - Passed (Score 100%)
        payload2 = {
            "answers": [
                {"question_id": q1.id, "choice_id": c1_correct.id},
                {"question_id": q2.id, "choice_id": c2_correct.id}
            ]
        }
        response = self.client.post(
            f"/api/quizzes/{quiz.id}/submit",
            data=json.dumps(payload2),
            content_type="application/json",
            **student_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["score"], 100)
        self.assertTrue(data["is_passed"])
        self.assertEqual(data["attempt_number"], 2)

        # 3. Third Attempt - Exceed Limit (400)
        response = self.client.post(
            f"/api/quizzes/{quiz.id}/submit",
            data=json.dumps(payload2),
            content_type="application/json",
            **student_headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Batas pengerjaan kuis telah habis", response.json()["message"])

    def test_certificate_verifications(self):
        # Generate dummy Certificate
        cert = Certificate.objects.create(
            student=self.student,
            course=self.course,
            certificate_code="CERT-TEST1234"
        )
        
        # Verify publicly
        response = self.client.get("/api/enrollments/certificates/verify/CERT-TEST1234")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["student_name"], self.student.username)
        self.assertEqual(data["course_title"], self.course.title)

        # Verify invalid code
        response = self.client.get("/api/enrollments/certificates/verify/CERT-FAKE")
        self.assertEqual(response.status_code, 404)
