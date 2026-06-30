from pymongo import MongoClient
from django.conf import settings

_client = None


def get_mongo_client() -> MongoClient:
    """Singleton MongoDB client."""
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URL)
    return _client


def get_db():
    """Kembalikan database LMS logs."""
    return get_mongo_client()[settings.MONGODB_DB]


def get_activity_logs_collection():
    """Collection untuk activity logs."""
    return get_db()["activity_logs"]


def get_learning_analytics_collection():
    """Collection untuk learning analytics."""
    return get_db()["learning_analytics"]
