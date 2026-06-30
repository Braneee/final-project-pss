from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-lab06-redis-mongo-celery-lms-key-2025"

DEBUG = True

ALLOWED_HOSTS = ['*']


# =============================================================================
# Aplikasi yang terdaftar
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "silk",           # Django Silk - query profiling
    "courses",        # App courses
    "accounts",       # App accounts - Auth & User Profile
    "enrollments",    # App enrollments - Pendaftaran kursus
    "activity_logs",  # App activity logs - MongoDB logging (BARU)
]


# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "silk.middleware.SilkyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "lms.wsgi.application"


# =============================================================================
# Database - PostgreSQL
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "lms_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "database",
        "PORT": "5432",
    }
}


# =============================================================================
# Redis Cache (BARU)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "lms",
        "TIMEOUT": 300,  # 5 menit default
    }
}

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Cache timeout spesifik
CACHE_TTL_COURSE_LIST = 60 * 5      # 5 menit
CACHE_TTL_COURSE_DETAIL = 60 * 10   # 10 menit

# =============================================================================
# MongoDB - Activity Logs (BARU)
# =============================================================================

MONGODB_URL = os.getenv(
    "MONGODB_URL",
    os.getenv("MONGO_URL", "mongodb://mongodb:27017/")
)
MONGODB_DB = "lms_logs"

# =============================================================================
# Celery + RabbitMQ
# =============================================================================

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//"
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://redis:6379/1"
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Jakarta"

CELERY_IMPORTS = (
    "enrollments.tasks",
    "courses.tasks",
)

# =============================================================================
# Celery Beat - Scheduled Tasks
# =============================================================================

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "update-course-statistics-daily": {
        "task": "courses.tasks.update_course_statistics",
        "schedule": crontab(hour=2, minute=0),
    },
}


# =============================================================================
# Rate Limiting (BARU)
# =============================================================================

RATELIMIT_USE_CACHE = "default"   # Pakai Redis cache


# =============================================================================
# JWT Configuration
# =============================================================================

JWT_SECRET_KEY                  = SECRET_KEY
JWT_ALGORITHM                   = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60    # 1 jam
JWT_REFRESH_TOKEN_EXPIRE_DAYS   = 7     # 7 hari


# =============================================================================
# Django Silk
# =============================================================================

SILKY_PYTHON_PROFILER = True
SILKY_META            = True


# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "id"
TIME_ZONE     = "Asia/Jakarta"
USE_I18N      = True
USE_TZ        = True


# =============================================================================
# Static dan Media files
# =============================================================================

STATIC_URL = "static/"
MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
