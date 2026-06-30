"""
AuthBearer - Custom JWT Authentication untuk Django Ninja

Cara kerja:
1. Client kirim header: Authorization: Bearer <access_token>
2. AuthBearer decode token, cari user di database
3. Set request.user supaya bisa diakses di view

Penggunaan di endpoint:
    @router.get("/protected", auth=AuthBearer())
    def my_view(request):
        user = request.user  # sudah terautentikasi
"""

import jwt
from django.contrib.auth.models import User
from ninja.security import HttpBearer
from ninja.errors import HttpError

from .jwt_helper import decode_token


class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str):
        """
        Dipanggil otomatis oleh Django Ninja setiap ada request ke endpoint protected.
        Return user object jika valid, raise error jika tidak.
        """
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise HttpError(401, "Access token sudah expired")
        except jwt.InvalidTokenError:
            raise HttpError(401, "Token tidak valid")

        if payload.get("type") != "access":
            raise HttpError(401, "Bukan access token")

        try:
            user = User.objects.select_related('profile').get(id=payload["sub"])
        except User.DoesNotExist:
            raise HttpError(401, "User tidak ditemukan")

        request.user = user
        return user

