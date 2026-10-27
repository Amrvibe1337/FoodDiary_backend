import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models import DiaryEntry, Product, Recipe
from app.models.user import User as UserModel
from app.nutrition import recipes_nutrition, round_nutrition
from app.schemas import MealCreate, MealOut

router = APIRouter(prefix="/meals", tags=["meals"])

HUNDRED = Decimal("100")
ZERO = Decimal("0")
MAX_GRAMS = Decimal("5000")


@router.get("", response_model=list[MealOut])
async def list_meals(
    entry_date: dt.date | None = Query(default=None, alias="date"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает записи дневника текущего пользователя за указанный день.
    Без параметра date отдаёт записи за сегодня.
    """
    target_date = entry_date or dt.date.today()
    meals = await db.scalars(
        select(DiaryEntry)
        .where(
            DiaryEntry.user_id == current_user.id,
            DiaryEntry.date == target_date,
        )
        .order_by(DiaryEntry.id)
    )
    return meals.all()


@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED)
async def create_meal(
    payload: MealCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Добавляет запись в дневник. Название и КБЖУ считаются по каталогу,
    значения из запроса игнорируются: запись должна быть снапшотом.
    """
    if payload.date > dt.date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date cannot be in the future",
        )

    if payload.type == "product":
        meal = await _product_meal(payload, current_user, db)
    else:
        meal = await _recipe_meal(payload, current_user, db)

    db.add(meal)
    await db.commit()
    return meal


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Удаляет запись дневника текущего пользователя.
    Чужая или несуществующая запись — 404.
    """
    meal = await db.scalar(
        select(DiaryEntry).where(
            DiaryEntry.id == meal_id,
            DiaryEntry.user_id == current_user.id,
        )
    )
    if meal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found",
        )

    await db.delete(meal)
    await db.commit()
    return None


async def _product_meal(
    payload: MealCreate, user: UserModel, db: AsyncSession
) -> DiaryEntry:
    if (
        payload.product_id is None
        or payload.amount_grams is None
        or payload.recipe_id is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product entry requires product_id and amount_grams only",
        )

    if not ZERO < payload.amount_grams < MAX_GRAMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_grams must be greater than 0 and less than 5000",
        )

    product = await db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    factor = payload.amount_grams / HUNDRED
    return DiaryEntry(
        user_id=user.id,
        item_type="product",
        product_id=product.id,
        recipe_id=None,
        item_name=product.product_name,
        amount_grams=payload.amount_grams,
        calories=round_nutrition(product.calories * factor),
        proteins=round_nutrition(product.proteins * factor),
        fats=round_nutrition(product.fats * factor),
        carbs=round_nutrition(product.carbs * factor),
        date=payload.date,
    )


async def _recipe_meal(
    payload: MealCreate, user: UserModel, db: AsyncSession
) -> DiaryEntry:
    if (
        payload.recipe_id is None
        or payload.product_id is not None
        or payload.amount_grams is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe entry requires recipe_id only",
        )

    recipe = await db.get(Recipe, payload.recipe_id)
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    nutrition = await recipes_nutrition(db, [recipe.id])
    values = nutrition.get(recipe.id)
    if values is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe has no ingredients",
        )

    calories, proteins, fats, carbs = values
    return DiaryEntry(
        user_id=user.id,
        item_type="recipe",
        product_id=None,
        recipe_id=recipe.id,
        item_name=recipe.recipe_name,
        amount_grams=None,
        calories=calories,
        proteins=proteins,
        fats=fats,
        carbs=carbs,
        date=payload.date,
    )
