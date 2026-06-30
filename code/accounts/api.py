"""
Auth API Endpoints menggunakan Django Ninja

Endpoints:
  POST /api/auth/register  - Daftar user baru
  POST /api/auth/login     - Login, dapat JWT tokens
  POST /api/auth/refresh   - Refresh access token
  GET  /api/auth/me        - Lihat profil sendiri
  PUT  /api/auth/me        - Update profil sendiri
"""

import jwt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from ninja import Router
from ninja.errors import HttpError

from .models import UserProfile
from .schemas import (
    RegisterSchema, LoginSchema, RefreshTokenSchema,
    UpdateProfileSchema, TokenOut, UserProfileOut, MessageOut
)
from .jwt_helper import create_access_token, create_refresh_token, decode_token
from .auth_bearer import AuthBearer

router = Router(tags=["Auth"])


def _build_user_out(user: User) -> UserProfileOut:
    """Helper: konversi User + Profile ke UserProfileOut schema."""
    profile = getattr(user, 'profile', None)
    return UserProfileOut(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=profile.role if profile else 'student',
        bio=profile.bio if profile else '',
    )


# -----------------------------------------------------------------------------
# POST /api/auth/register
# -----------------------------------------------------------------------------
@router.post("/register", response={201: TokenOut, 400: MessageOut})
def register(request, data: RegisterSchema):
    """
    Daftarkan user baru.
    Otomatis login dan kembalikan JWT tokens.
    """
    # Cek username sudah ada
    if User.objects.filter(username=data.username).exists():
        return 400, {"message": "Username sudah digunakan"}

    # Cek email sudah ada
    if User.objects.filter(email=data.email).exists():
        return 400, {"message": "Email sudah digunakan"}

    # Buat user
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),
        first_name=data.first_name or "",
        last_name=data.last_name or "",
    )

    # Buat profile
    profile = UserProfile.objects.create(user=user, role=data.role)

    # Generate tokens
    access_token  = create_access_token(user.id, user.username, profile.role)
    refresh_token = create_refresh_token(user.id)

    return 201, TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_out(user),
    )


# -----------------------------------------------------------------------------
# POST /api/auth/login
# -----------------------------------------------------------------------------
@router.post("/login", response={200: TokenOut, 401: MessageOut})
def login(request, data: LoginSchema):
    """Login dengan username & password. Kembalikan JWT tokens."""
    try:
        user = User.objects.select_related('profile').get(username=data.username)
    except User.DoesNotExist:
        return 401, {"message": "Username atau password salah"}

    if not check_password(data.password, user.password):
        return 401, {"message": "Username atau password salah"}

    profile = getattr(user, 'profile', None)
    role = profile.role if profile else 'student'

    access_token  = create_access_token(user.id, user.username, role)
    refresh_token = create_refresh_token(user.id)

    return 200, TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_out(user),
    )


# -----------------------------------------------------------------------------
# POST /api/auth/refresh
# -----------------------------------------------------------------------------
@router.post("/refresh", response={200: dict, 401: MessageOut})
def refresh_token(request, data: RefreshTokenSchema):
    """
    Gunakan refresh token untuk mendapatkan access token baru.
    Refresh token tidak berubah (tetap sama).
    """
    try:
        payload = decode_token(data.refresh_token)
    except jwt.ExpiredSignatureError:
        return 401, {"message": "Refresh token sudah expired, silakan login ulang"}
    except jwt.InvalidTokenError:
        return 401, {"message": "Refresh token tidak valid"}

    if payload.get("type") != "refresh":
        return 401, {"message": "Token bukan refresh token"}

    try:
        user    = User.objects.select_related('profile').get(id=payload["sub"])
        profile = getattr(user, 'profile', None)
        role    = profile.role if profile else 'student'
    except User.DoesNotExist:
        return 401, {"message": "User tidak ditemukan"}

    new_access_token = create_access_token(user.id, user.username, role)

    return 200, {
        "access_token":  new_access_token,
        "refresh_token": data.refresh_token,
        "token_type":    "bearer",
    }


# -----------------------------------------------------------------------------
# GET /api/auth/me
# -----------------------------------------------------------------------------
@router.get("/me", response={200: UserProfileOut, 401: MessageOut}, auth=AuthBearer())
def get_me(request):
    """Ambil profil user yang sedang login. Butuh JWT token."""
    return 200, _build_user_out(request.user)


# -----------------------------------------------------------------------------
# PUT /api/auth/me
# -----------------------------------------------------------------------------
@router.put("/me", response={200: UserProfileOut, 401: MessageOut}, auth=AuthBearer())
def update_me(request, data: UpdateProfileSchema):
    """Update profil user yang sedang login."""
    user    = request.user
    profile = getattr(user, 'profile', None)

    # Update field User
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.email is not None:
        if User.objects.exclude(id=user.id).filter(email=data.email).exists():
            raise HttpError(400, "Email sudah digunakan user lain")
        user.email = data.email
    user.save()

    # Update field Profile
    if profile and data.bio is not None:
        profile.bio = data.bio
        profile.save()

    return 200, _build_user_out(user)
