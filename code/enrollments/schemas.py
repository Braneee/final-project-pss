"""Pydantic Schemas untuk App Enrollments"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class EnrollSchema(BaseModel):
    """Body untuk POST /api/enrollments"""
    course_id: int


class ProgressSchema(BaseModel):
    """Body untuk POST /api/enrollments/{id}/progress"""
    content_id:  int
    is_complete: bool = True


class CourseSimpleOut(BaseModel):
    id:    int
    title: str
    level: str
    price: int


class EnrollmentOut(BaseModel):
    id:          int
    course:      CourseSimpleOut
    enrolled_at: datetime
    is_active:   bool


class ProgressOut(BaseModel):
    content_id:   int
    content_title: str
    is_complete:  bool
    completed_at: Optional[datetime]


class MessageOut(BaseModel):
    message: str


# =============================================================================
# QUIZ ATTEMPT & CERTIFICATE SCHEMAS (BARU)
# =============================================================================

class QuizAttemptOut(BaseModel):
    id:             int
    quiz_id:        int
    score:          int
    is_passed:      bool
    attempt_number: int
    started_at:     datetime
    completed_at:   datetime

    class Config:
        from_attributes = True


class CertificateOut(BaseModel):
    id:               int
    course_title:     str
    certificate_code: str
    pdf_url:          Optional[str] = None
    issued_at:        datetime

    class Config:
        from_attributes = True

