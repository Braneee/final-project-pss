from django.contrib import admin
from .models import Course, CourseMember, CourseContent


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'level', 'price', 'is_published', 'created_at')
    list_filter = ('instructor', 'level', 'is_published', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)


@admin.register(CourseMember)
class CourseMemberAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'user_id', 'roles')
    list_filter = ('roles',)


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'description')