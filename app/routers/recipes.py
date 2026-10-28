from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_admin
from app.db_depends import get_async_db
from app.models.food import Recipe, RecipeIngredient, RecipeStep, Product
from app.models.diary import Favorite
from app.models.user import User as UserModel
from app.schemas import (
    RecipeCreate, RecipeUpdate, RecipeOut, RecipeMacrosOut,
    RecipeIngredientOut, RecipeStepOut, RecipeCategory,
)
from app.utils.nutrition import recipes_nutrition 
from app.utils.recipes_func import  _load_options, _serialize, _load_recipe_full, _favorite_ids, _validate_unique_ingredients, _validate_unique_steps, _ensure_products_exist 


router = APIRouter(prefix="/recipes", tags=["recipes"])

# ---------- Чтение (доступно user + admin) ----------

@router.get("", response_model=list[RecipeOut])
async def list_recipes(
    search: str | None = None,
    category: RecipeCategory | None = None,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-10. Список рецептов с поиском и фильтром по категории."""
    stmt = select(Recipe).options(*_load_options())
    if search:
        stmt = stmt.where(Recipe.recipe_name.ilike(f"%{search}%"))
    if category:
        stmt = stmt.where(Recipe.category == category)
    stmt = stmt.order_by(Recipe.recipe_name)

    recipes = list(await db.scalars(stmt))
    if not recipes:
        return []

    # Один SQL на все рецепты
    macros_map = await recipes_nutrition(db, [r.id for r in recipes])
    fav = await _favorite_ids(db, current_user.id, [r.id for r in recipes])

    return [
        _serialize(r, macros_map.get(r.id, (0, 0, 0, 0)), r.id in fav)
        for r in recipes
    ]


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-11. Карточка рецепта."""
    recipe = await _load_recipe_full(db, recipe_id)
    macros_map = await recipes_nutrition(db, [recipe.id])
    fav = await _favorite_ids(db, current_user.id, [recipe.id])
    return _serialize(recipe, macros_map.get(recipe.id, (0, 0, 0, 0)), recipe.id in fav)


# ---------- CRUD (доступно только admin) ----------

@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    payload: RecipeCreate,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-21. Создание рецепта."""
    _validate_unique_ingredients(payload.ingredients)
    _validate_unique_steps(payload.steps)
    await _ensure_products_exist(db, [i.product_id for i in payload.ingredients])

    recipe = Recipe(
        recipe_name=payload.recipe_name,
        category=payload.category,
        description=payload.description,
        image_path=payload.image_path,
        ingredients=[
            RecipeIngredient(product_id=i.product_id, amount_grams=i.amount_grams)
            for i in payload.ingredients
        ],
        steps=[
            RecipeStep(step_number=s.step_number, description=s.description)
            for s in payload.steps
        ],
    )
    db.add(recipe)
    await db.commit()

    recipe = await _load_recipe_full(db, recipe.id)
    macros_map = await recipes_nutrition(db, [recipe.id])
    return _serialize(recipe, macros_map.get(recipe.id, (0, 0, 0, 0)), False)


@router.patch("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-21. Изменение рецепта. Если переданы ingredients/steps — полная замена."""
    recipe = await _load_recipe_full(db, recipe_id)

    if payload.recipe_name is not None:
        recipe.recipe_name = payload.recipe_name
    if payload.category is not None:
        recipe.category = payload.category
    if payload.description is not None:
        recipe.description = payload.description
    if payload.image_path is not None:
        recipe.image_path = payload.image_path

    if payload.ingredients is not None:
        _validate_unique_ingredients(payload.ingredients)
        await _ensure_products_exist(db, [i.product_id for i in payload.ingredients])
        recipe.ingredients = [
            RecipeIngredient(product_id=i.product_id, amount_grams=i.amount_grams)
            for i in payload.ingredients
        ]

    if payload.steps is not None:
        _validate_unique_steps(payload.steps)
        recipe.steps = [
            RecipeStep(step_number=s.step_number, description=s.description)
            for s in payload.steps
        ]

    await db.commit()

    recipe = await _load_recipe_full(db, recipe_id)
    macros_map = await recipes_nutrition(db, [recipe.id])
    fav = await _favorite_ids(db, current_admin.id, [recipe.id])
    return _serialize(recipe, macros_map.get(recipe.id, (0, 0, 0, 0)), recipe.id in fav)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-21. Удаление рецепта. Каскад по БД, дневник сохранит snapshot."""
    recipe = await db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    await db.delete(recipe)
    await db.commit()
    return None
