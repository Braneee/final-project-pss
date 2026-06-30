"""Pydantic Schemas untuk App Courses"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# =============================================================================
# INPUT SCHEMAS
# =============================================================================

class CourseCreateSchema(BaseModel):
    """Schema untuk POST /api/courses (buat course baru)"""
    title:        str
    description:  Optional[str] = ""
    price:        Optional[int] = 0
    level:        Optional[str] = "beginner"   # beginner | intermediate | advanced
    is_published: Optional[bool] = True


class CourseUpdateSchema(BaseModel):
    """Schema untuk PATCH /api/courses/{id} (update sebagian field)"""
    title:        Optional[str]  = None
    description:  Optional[str]  = None
    price:        Optional[int]  = None
    level:        Optional[str]  = None
    is_published: Optional[bool] = None


# =============================================================================
# FILTER / QUERY PARAMS
# =============================================================================

class CourseFilterSchema(BaseModel):
    """Query params untuk GET /api/courses?level=beginner&max_price=100000"""
    level:     Optional[str] = None
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    search:    Optional[str] = None   # cari di title
    page:      int = 1
    page_size: int = 10


# =============================================================================
# OUTPUT SCHEMAS
# =============================================================================

class InstructorOut(BaseModel):
    id:       int
    username: str
    email:    str


class CourseOut(BaseModel):
    """Response untuk satu course"""
    id:           int
    title:        str
    description:  str
    price:        int
    level:        str
    is_published: bool
    instructor:   InstructorOut
    created_at:   datetime

    class Config:
        from_attributes = True


class CourseListOut(BaseModel):
    """Response untuk list course dengan pagination"""
    total:    int
    page:     int
    per_page: int
    results:  List[CourseOut]


class MessageOut(BaseModel):
    message: str


# =============================================================================
# QUIZ SCHEMAS (BARU)
# =============================================================================

class ChoiceCreateSchema(BaseModel):
    text:       str
    is_correct: bool = False


class QuestionCreateSchema(BaseModel):
    text:   str
    weight: Optional[int] = 10
    choices: List[ChoiceCreateSchema]


class QuizCreateSchema(BaseModel):
    course_id:     int
    title:         str
    description:   Optional[str] = ""
    passing_grade: Optional[int] = 70
    attempt_limit: Optional[int] = 3
    lesson_id:     Optional[int] = None



class QuizUpdateSchema(BaseModel):
    title:         Optional[str] = None
    description:   Optional[str] = None
    passing_grade: Optional[int] = None
    attempt_limit: Optional[int] = None
    lesson_id:     Optional[int] = None


class QuestionUpdateSchema(BaseModel):
    text:   Optional[str] = None
    weight: Optional[int] = None



class ChoiceOut(BaseModel):
    id:   int
    text: str

    class Config:
        from_attributes = True


class ChoiceInstructorOut(BaseModel):
    id:         int
    text:       str
    is_correct: bool

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id:      int
    text:    str
    weight:  int
    choices: List[ChoiceOut]

    class Config:
        from_attributes = True


class QuestionInstructorOut(BaseModel):
    id:      int
    text:    str
    weight:  int
    choices: List[ChoiceInstructorOut]

    class Config:
        from_attributes = True


class QuizOut(BaseModel):
    id:            int
    course_id:     int
    lesson_id:     Optional[int] = None
    title:         str
    description:   str
    passing_grade: int
    attempt_limit: int
    questions:     List[QuestionOut]

    class Config:
        from_attributes = True


class QuizInstructorOut(BaseModel):
    id:            int
    course_id:     int
    lesson_id:     Optional[int] = None
    title:         str
    description:   str
    passing_grade: int
    attempt_limit: int
    questions:     List[QuestionInstructorOut]

    class Config:
        from_attributes = True


class ChoiceSubmitSchema(BaseModel):
    question_id: int
    choice_id:   int


class QuizSubmitSchema(BaseModel):
    answers: List[ChoiceSubmitSchema]


class QuizSubmitResultOut(BaseModel):
    score:          int
    passing_grade:  int
    is_passed:      bool
    attempt_number: int
    attempt_limit:  int
    message:        str

