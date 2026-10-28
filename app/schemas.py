import datetime as dt
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime
from typing import Annotated, Literal
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


class MealCreate(BaseModel):
    """
    Запись в дневник: для продукта нужны product_id и amount_grams,
    для рецепта — только recipe_id (рецепт добавляется одной порцией).
    """

    type: Literal["product", "recipe"]
    date: dt.date
    product_id: int | None = None
    recipe_id: int | None = None
    amount_grams: Decimal | None = None


class MealOut(BaseModel):
    """
    Запись дневника на выход. Это снапшот: значения берутся из самой записи,
    а не из текущего состояния каталога.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    item_name: str
    product_id: int | None
    recipe_id: int | None
    amount_grams: float | None
    calories: float
    proteins: float
    fats: float
    carbs: float
    date: dt.date


class FavoriteCreate(BaseModel):
    """
    Добавление в избранное: ровно одно из полей.
    """

    product_id: int | None = None
    recipe_id: int | None = None


class FavoriteProductOut(BaseModel):
    """
    Продукт в избранном: КБЖУ на 100 г.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    product_name: str
    image_path: str | None
    calories: float
    proteins: float
    fats: float
    carbs: float


class FavoriteRecipeOut(BaseModel):
    """
    Рецепт в избранном: КБЖУ на одну порцию, считается по ингредиентам.
    """

    id: int
    recipe_name: str
    category: str
    description: str | None
    image_path: str | None
    calories: float
    proteins: float
    fats: float
    carbs: float


class FavoriteOut(BaseModel):
    """
    Элемент избранного с вложенными данными каталога.
    Заполнено либо product, либо recipe.
    """

    id: int
    product_id: int | None
    recipe_id: int | None
    product: FavoriteProductOut | None = None
    recipe: FavoriteRecipeOut | None = None


class PostCreate(BaseModel):
    """
    Текст нового поста.
    """

    content: str


class PostOut(BaseModel):
    """
    Пост в ленте: автор, счётчики и признак лайка текущего пользователя.
    """

    id: int
    user_id: int
    author_name: str
    content: str
    created_at: dt.datetime
    likes_count: int
    liked: bool
    comments_count: int


class CommentCreate(BaseModel):
    """
    Текст нового комментария.
    """

    content: str


class CommentOut(BaseModel):
    """
    Комментарий к посту.
    """

    id: int
    post_id: int
    user_id: int
    author_name: str
    content: str
    created_at: dt.datetime


class LikeOut(BaseModel):
    """
    Состояние лайка после операции.
    """

    liked: bool
    likes_count: int
