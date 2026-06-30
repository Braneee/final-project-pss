"""
Activity Logger - Menyimpan log aktivitas ke MongoDB
"""

from datetime import datetime, timezone
from lms.mongodb import get_activity_logs_collection, get_learning_analytics_collection


def log_activity(user_id: int, username: str, action: str, resource: str,
                 resource_id: int = None, extra: dict = None):
    """
    Simpan satu entri activity log ke MongoDB.

    Parameters:
        user_id     : ID user Django
        username    : username string
        action      : "enroll", "view_course", "complete_lesson", "login", dsb.
        resource    : "course", "lesson", "user", dsb.
        resource_id : ID objek yang terlibat (opsional)
        extra       : data tambahan bebas (opsional)
    """
    doc = {
        "user_id":     user_id,
        "username":    username,
        "action":      action,
        "resource":    resource,
        "resource_id": resource_id,
        "extra":       extra or {},
        "timestamp":   datetime.now(timezone.utc),
    }
    get_activity_logs_collection().insert_one(doc)


def log_learning_analytics(user_id: int, course_id: int, event: str, data: dict = None):
    """
    Simpan event analytics pembelajaran ke MongoDB.

    Parameters:
        user_id   : ID user Django
        course_id : ID course terkait
        event     : "lesson_started", "lesson_completed", "course_completed", dsb.
        data      : data tambahan (opsional)
    """
    doc = {
        "user_id":   user_id,
        "course_id": course_id,
        "event":     event,
        "data":      data or {},
        "timestamp": datetime.now(timezone.utc),
    }
    get_learning_analytics_collection().insert_one(doc)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def get_user_activity_summary(user_id: int) -> list:
    """Ringkasan aktivitas per action untuk satu user."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort":  {"count": -1}},
    ]
    return list(get_activity_logs_collection().aggregate(pipeline))


def get_course_enrollment_stats() -> list:
    """Statistik enrollment per course dari activity logs."""
    pipeline = [
        {"$match": {"action": "enroll", "resource": "course"}},
        {"$group": {"_id": "$resource_id", "total_enrollments": {"$sum": 1}}},
        {"$sort":  {"total_enrollments": -1}},
        {"$limit": 10},
    ]
    return list(get_activity_logs_collection().aggregate(pipeline))


def get_recent_activities(limit: int = 50) -> list:
    """Ambil aktivitas terbaru (semua user)."""
    return list(
        get_activity_logs_collection()
        .find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
