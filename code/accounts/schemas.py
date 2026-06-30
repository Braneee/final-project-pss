"""
Pydantic Schemas untuk App Accounts

Schema digunakan oleh Django Ninja untuk:
1. Validasi input request (body, query params)
2. Serialisasi output response
3. Auto-generate dokumentasi Swagger
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


# =============================================================================
# INPUT SCHEMAS (Request Body)
# =============================================================================

class RegisterSchema(BaseModel):
    """Schema untuk endpoint POST /api/auth/register"""
    username:   str
    email:      EmailStr
    password:   str
    first_name: Optional[str] = ""
    last_name:  Optional[str] = ""
    role:       Optional[str] = "student"   # student | instructor | admin

    @field_validator('username')
    @classmethod
    def username_min_length(cls, v):
        if len(v) < 3:
            raise ValueError('Username minimal 3 karakter')
        return v

    @field_validator('password')
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError('Password minimal 6 karakter')
        return v

    @field_validator('role')
    @classmethod
    def role_valid(cls, v):
        allowed = ['student', 'instructor', 'admin']
        if v not in allowed:
            raise ValueError(f'Role harus salah satu dari: {allowed}')
        return v


class LoginSchema(BaseModel):
    """Schema untuk endpoint POST /api/auth/login"""
    username: str
    password: str


class RefreshTokenSchema(BaseModel):
    """Schema untuk endpoint POST /api/auth/refresh"""
    refresh_token: str


class UpdateProfileSchema(BaseModel):
    """Schema untuk endpoint PUT /api/auth/me"""
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    email:      Optional[EmailStr] = None
    bio:        Optional[str] = None


# =============================================================================
# OUTPUT SCHEMAS (Response)
# =============================================================================

class UserProfileOut(BaseModel):
    """Data profil user yang dikembalikan ke client"""
    id:         int
    username:   str
    email:      str
    first_name: str
    last_name:  str
    role:       str
    bio:        str

    class Config:
        from_attributes = True  # Bisa dibuat dari Django model instance


class TokenOut(BaseModel):
    """Response ketika login atau register berhasil"""
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          UserProfileOut


class MessageOut(BaseModel):
    """Response pesan sederhana"""
    message: str
