from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_current_admin
from app.db_depends import get_async_db

from app.models.food import Recipe, RecipeIngredient, RecipeStep, Product
from app.models.diary import Favorite
from app.models.user import User as UserModel
from app.schemas import (
    RecipeCreate, RecipeUpdate, RecipeOut, RecipeMacrosOut,
    RecipeIngredientOut, RecipeStepOut, RecipeCategory,
)
# ---------- Хелперы ----------

def _load_options():
    return (
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.product),
        selectinload(Recipe.steps),
    )


def _serialize(recipe: Recipe, macros: tuple, is_favorite: bool) -> RecipeOut:
    cal, prot, fat, carb = macros
    return RecipeOut(
        id=recipe.id,
        recipe_name=recipe.recipe_name,
        category=recipe.category,
        description=recipe.description,
        image_path=recipe.image_path,
        macros=RecipeMacrosOut(
            calories=float(cal),
            proteins=float(prot),
            fats=float(fat),
            carbs=float(carb),
        ),
        ingredients=[
            RecipeIngredientOut(
                product_id=i.product_id,
                product_name=i.product.product_name,
                amount_grams=float(i.amount_grams),
            )
            for i in recipe.ingredients
        ],
        steps=[
            RecipeStepOut(step_number=s.step_number, description=s.description)
            for s in sorted(recipe.steps, key=lambda s: s.step_number)
        ],
        is_favorite=is_favorite,
    )


async def _load_recipe_full(db: AsyncSession, recipe_id: int) -> Recipe:
    stmt = select(Recipe).where(Recipe.id == recipe_id).options(*_load_options())
    recipe = (await db.scalars(stmt)).first()
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    return recipe


async def _favorite_ids(db: AsyncSession, user_id: int, recipe_ids: list[int]) -> set[int]:
    if not recipe_ids:
        return set()
    rows = await db.scalars(
        select(Favorite.recipe_id)
        .where(Favorite.user_id == user_id, Favorite.recipe_id.in_(recipe_ids))
    )
    return {rid for rid in rows if rid is not None}


def _validate_unique_ingredients(items) -> None:
    ids = [i.product_id for i in items]
    if len(ids) != len(set(ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Duplicate products in ingredients")


def _validate_unique_steps(items) -> None:
    nums = [s.step_number for s in items]
    if len(nums) != len(set(nums)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Duplicate step_number in steps")


async def _ensure_products_exist(db: AsyncSession, product_ids: list[int]) -> None:
    existing = set(await db.scalars(select(Product.id).where(Product.id.in_(product_ids))))
    missing = set(product_ids) - existing
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Products not found: {sorted(missing)}"
        )
