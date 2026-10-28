from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models import Favorite, Product, Recipe
from app.models.user import User as UserModel
from app.utils.nutrition import recipes_nutrition
from app.schemas import (
    FavoriteCreate,
    FavoriteOut,
    FavoriteProductOut,
    FavoriteRecipeOut,
)

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteOut])
async def list_favorites(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает избранное текущего пользователя с данными каталога.
    Продукты — КБЖУ на 100 г, рецепты — КБЖУ на одну порцию.
    """
    favorites = (
        await db.scalars(
            select(Favorite)
            .where(Favorite.user_id == current_user.id)
            .options(selectinload(Favorite.product), selectinload(Favorite.recipe))
            .order_by(Favorite.id)
        )
    ).all()

    recipe_ids = [
        favorite.recipe_id for favorite in favorites if favorite.recipe_id is not None
    ]
    nutrition = await recipes_nutrition(db, recipe_ids)

    result: list[FavoriteOut] = []
    for favorite in favorites:
        if favorite.product is not None:
            result.append(
                FavoriteOut(
                    id=favorite.id,
                    product_id=favorite.product_id,
                    recipe_id=None,
                    product=FavoriteProductOut.model_validate(favorite.product),
                )
            )
            continue

        if favorite.recipe is not None:
            values = nutrition.get(favorite.recipe_id) or (0, 0, 0, 0)
            result.append(
                FavoriteOut(
                    id=favorite.id,
                    product_id=None,
                    recipe_id=favorite.recipe_id,
                    recipe=FavoriteRecipeOut(
                        id=favorite.recipe.id,
                        recipe_name=favorite.recipe.recipe_name,
                        category=favorite.recipe.category,
                        description=favorite.recipe.description,
                        image_path=favorite.recipe.image_path,
                        calories=float(values[0]),
                        proteins=float(values[1]),
                        fats=float(values[2]),
                        carbs=float(values[3]),
                    ),
                )
            )

    return result


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(
    payload: FavoriteCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Добавляет продукт или рецепт в избранное. Нужно ровно одно поле.
    Повторное добавление не считается ошибкой.
    """
    has_product = payload.product_id is not None
    has_recipe = payload.recipe_id is not None
    if has_product == has_recipe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of product_id or recipe_id is required",
        )

    if has_product:
        if await db.get(Product, payload.product_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        exists = await db.scalar(
            select(Favorite.id).where(
                Favorite.user_id == current_user.id,
                Favorite.product_id == payload.product_id,
            )
        )
        if exists is not None:
            return None
        db.add(Favorite(user_id=current_user.id, product_id=payload.product_id))
    else:
        if await db.get(Recipe, payload.recipe_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found",
            )
        exists = await db.scalar(
            select(Favorite.id).where(
                Favorite.user_id == current_user.id,
                Favorite.recipe_id == payload.recipe_id,
            )
        )
        if exists is not None:
            return None
        db.add(Favorite(user_id=current_user.id, recipe_id=payload.recipe_id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return None


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product_favorite(
    product_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Убирает продукт из избранного. Отсутствие записи не считается ошибкой.
    """
    await _remove_favorite(db, current_user, Favorite.product_id == product_id)
    return None


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipe_favorite(
    recipe_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Убирает рецепт из избранного. Отсутствие записи не считается ошибкой.
    """
    await _remove_favorite(db, current_user, Favorite.recipe_id == recipe_id)
    return None


async def _remove_favorite(db: AsyncSession, user: UserModel, condition) -> None:
    favorite = await db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, condition)
    )
    if favorite is None:
        return

    await db.delete(favorite)
    await db.commit()
