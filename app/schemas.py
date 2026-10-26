from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime
from typing import Annotated
from fastapi import Form


class UserCreate(BaseModel):
    """
    Модель для регистрации нового пользователя
    """
    name: str = Field(..., description="Имя и фамилия пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символов)")


class User(BaseModel):
    """
    Модель для ответа после создания нового пользователя
    """
    id: int = Field(..., description="Уникальный идентификатор пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    role: str = Field(..., description="Роль: 'user'")

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """
    Модель для создания(получения) refresh-токена 
    """
    refresh_token: str


class ProfileStats(BaseModel):
    """
    Статистика профиля
    """
    diary_entries_count: int
    diary_days_count: int
    favorites_count: int


class ProfileOut(BaseModel):
    """
    Данные профиля на выход
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime
    stats: ProfileStats


class ProfileUpdate(BaseModel):
    # Проверку длины делаем вручную в эндпоинте, чтобы вернуть 400, а не 422
    # (п. 7 ТЗ: некорректные данные — 400).
    name: str = Field(max_length=255)
