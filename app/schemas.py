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
    role: str = Field(default="user", 
                      pattern="^(user|admin)$", 
                      description="Роль: 'user' или 'admin'")


class User(BaseModel):
    """
    Модель для ответа после создания нового пользователя
    """
    id: int = Field(..., description="Уникальный идентификатор пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    role: str = Field(..., description="Роль: 'user' или 'admin'")

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """
    Модель для создания(получения) refresh-токена 
    """
    refresh_token: str
