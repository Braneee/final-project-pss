"""
Views untuk Simple LMS - Lab 05: Optimasi Database

File ini dibagi menjadi 3 bagian:

  BAGIAN 1 - Views dengan N+1 Problem
    Gunakan Django Silk (http://localhost:8000/silk/) untuk mengamati
    jumlah query yang dihasilkan oleh setiap endpoint.

  BAGIAN 2 - Views Teroptimasi (Referensi Solusi)
    Bandingkan jumlah query di Silk setelah mengakses endpoint ini.

  BAGIAN 3 - Statistik
    Contoh penggunaan aggregate() untuk kalkulasi di level database.

Petunjuk Lab:
  1. Jalankan python manage.py seed_data untuk mengisi data
  2. Akses endpoint BAGIAN 1, amati jumlah query di Silk
  3. Coba optimalkan sendiri sebelum melihat BAGIAN 2
  4. Bandingkan hasilnya
"""

from django.db.models import Avg, Count, Max, Min, Prefetch
from django.http import JsonResponse
from django.db.models import Avg, Max, Min, Count
from .models import Course, CourseContent, CourseMember
from django.db.models import F

def course_list_baseline(request):
    courses = Course.objects.all()
    data = []
    for c in courses:
        data.append({
            'course': c.name,
            'teacher': c.teacher.username,
        })
    return JsonResponse({'data': data})

def course_list_optimized(request):
    courses = Course.objects.select_related('teacher').all()
    data = []
    for c in courses:
        data.append({
            'course': c.name,
            'teacher': c.teacher.username,
        })
    return JsonResponse({'data': data})

def course_members_baseline(request):
    courses = Course.objects.all()
    payload = []

    for c in courses:
        member_count = CourseMember.objects.filter(course_id=c.id).count()

        payload.append({
            'course': c.name,
            'member_count': member_count
        })

    return JsonResponse({'data': payload})

def course_members_optimized(request):
    courses = Course.objects.prefetch_related('coursemember_set').all()
    payload = []

    for c in courses:
        payload.append({
            'course': c.name,
            'member_count': c.coursemember_set.count()
        })

    return JsonResponse({'data': payload})

def course_dashboard_baseline(request):
    courses = Course.objects.all()

    total = courses.count()
    prices = [c.price for c in courses]

    max_price = max(prices) if prices else 0
    min_price = min(prices) if prices else 0
    avg_price = sum(prices) / len(prices) if prices else 0

    return JsonResponse({
        'total': total,
        'max_price': max_price,
        'min_price': min_price,
        'avg_price': avg_price,
    })

def course_dashboard_optimized(request):
    stats = Course.objects.aggregate(
        total=Count('id'),
        max_price=Max('price'),
        min_price=Min('price'),
        avg_price=Avg('price'),
    )

    return JsonResponse(stats)

    return JsonResponse(stats)

def course_combined(request):
    courses = Course.objects.select_related('teacher').prefetch_related(
        'coursemember_set',
        'coursecontent_set__comment_set',
    )

    data = []

    for c in courses:
        data.append({
            'course': c.name,
            'teacher': c.teacher.username,
            'member_count': c.coursemember_set.count(),
        })

    return JsonResponse({'data': data})

def bulk_insert(request):
    course = Course.objects.first()

    contents = [
        CourseContent(name=f'Content {i}', course_id=course)
        for i in range(1000)
    ]

    CourseContent.objects.bulk_create(contents, batch_size=500)

    return JsonResponse({'status': 'bulk insert done'})

def bulk_update(request):
    Course.objects.all().update(price=F('price') * 1.1)

    return JsonResponse({'status': 'bulk update done'})

from django.shortcuts import render
def demo_view(request):
    return render(request, 'courses/demo.html')

def login_view(request):
    return render(request, 'courses/login.html')

    