"""
Activity Logs API - Query MongoDB logs

GET /api/logs/activities        - Log aktivitas terbaru (Admin)
GET /api/logs/user/{id}         - Ringkasan aktivitas satu user (Admin)
GET /api/logs/course-stats      - Statistik enrollment dari logs (Admin)
GET /api/logs/analytics         - Learning analytics terbaru (Admin)
"""

from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any

from accounts.auth_bearer import AuthBearer
from accounts.permissions import is_admin
from .logger import (
    get_recent_activities,
    get_user_activity_summary,
    get_course_enrollment_stats,
)
from lms.mongodb import get_learning_analytics_collection

router = Router(tags=["Activity Logs"])


class ActivityOut(BaseModel):
    user_id:     int
    username:    str
    action:      str
    resource:    str
    resource_id: Optional[int] = None
    extra:       dict = {}
    timestamp:   datetime

    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    action: str
    count:  int


class CourseStatOut(BaseModel):
    course_id:        int
    total_enrollments: int


class MessageOut(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# GET /api/logs/activities
# ---------------------------------------------------------------------------

@router.get("/activities", response=List[dict], auth=AuthBearer())
@is_admin
def recent_activities(request, limit: int = 50):
    """Ambil log aktivitas terbaru dari MongoDB. Hanya Admin."""
    docs = get_recent_activities(limit=min(limit, 200))
    # Serialisasi datetime menjadi string
    for d in docs:
        if "timestamp" in d:
            d["timestamp"] = d["timestamp"].isoformat()
    return docs


# ---------------------------------------------------------------------------
# GET /api/logs/user/{user_id}
# ---------------------------------------------------------------------------

@router.get("/user/{user_id}", response=List[SummaryOut], auth=AuthBearer())
@is_admin
def user_activity_summary(request, user_id: int):
    """Ringkasan aktivitas per action untuk satu user. Hanya Admin."""
    raw = get_user_activity_summary(user_id)
    return [SummaryOut(action=r["_id"], count=r["count"]) for r in raw]


# ---------------------------------------------------------------------------
# GET /api/logs/course-stats
# ---------------------------------------------------------------------------

@router.get("/course-stats", response=List[CourseStatOut], auth=AuthBearer())
@is_admin
def course_enrollment_stats(request):
    """Statistik 10 course dengan enrollment terbanyak dari MongoDB. Hanya Admin."""
    raw = get_course_enrollment_stats()
    return [CourseStatOut(course_id=r["_id"], total_enrollments=r["total_enrollments"]) for r in raw]


# ---------------------------------------------------------------------------
# GET /api/logs/analytics
# ---------------------------------------------------------------------------

@router.get("/analytics", response=List[dict], auth=AuthBearer())
@is_admin
def learning_analytics(request, limit: int = 50):
    """Ambil learning analytics terbaru. Hanya Admin."""
    docs = list(
        get_learning_analytics_collection()
        .find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(min(limit, 200))
    )
    for d in docs:
        if "timestamp" in d:
            d["timestamp"] = d["timestamp"].isoformat()
    return docs
