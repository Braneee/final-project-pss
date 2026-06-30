"""
Models untuk App Accounts

UserProfile menyimpan data tambahan user selain yang sudah ada di Django User:
- role: student / instructor / admin
- bio: deskripsi singkat
- avatar: foto profil
"""

from django.db import models
from django.contrib.auth.models import User


class ROLE(models.TextChoices):
    STUDENT    = 'student',    'Siswa'
    INSTRUCTOR = 'instructor', 'Instruktur'
    ADMIN      = 'admin',      'Admin'


class UserProfile(models.Model):
    """
    Ekstensi dari model User bawaan Django.
    Relasi One-to-One: satu User punya tepat satu UserProfile.
    """
    user   = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Pengguna'
    )
    role   = models.CharField(
        'Peran',
        max_length=20,
        choices=ROLE.choices,
        default=ROLE.STUDENT
    )
    bio    = models.TextField('Bio', blank=True, default='')
    avatar = models.ImageField('Avatar', upload_to='avatars/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    class Meta:
        verbose_name        = 'Profil Pengguna'
        verbose_name_plural = 'Profil Pengguna'
