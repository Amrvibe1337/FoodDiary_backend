from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_admin
from app.db_depends import get_async_db
from app.models import Category, Favorite, Product, RecipeIngredient
from app.models.user import User as UserModel
from app.schemas import ProductOut, ProductCreate, ProductUpdate

from app.utils.products_func import _favorite_ids, _ensure_category_exists

router = APIRouter(prefix="/products", tags=["products"])


# ---------- Чтение (user + admin) ----------

@router.get("", response_model=list[ProductOut])
async def list_products(
    search: str | None = None,
    category: str | None = None,     # slug, как в ТЗ: category=meat
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-08. Список продуктов с КБЖУ на 100 г, поиск по названию, фильтр по slug категории."""
    stmt = select(Product)
    if search:
        stmt = stmt.where(Product.product_name.ilike(f"%{search}%"))
    if category:
        stmt = stmt.join(Category, Category.id == Product.category_id).where(Category.slug == category)
    stmt = stmt.order_by(Product.product_name)

    products = list(await db.scalars(stmt))
    if not products:
        return []

    fav = await _favorite_ids(db, current_user.id, [p.id for p in products])
    return [
        ProductOut.model_validate(p).model_copy(update={"is_favorite": p.id in fav})
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Карточка продукта — пригодится для страницы добавления в дневник."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    fav = await _favorite_ids(db, current_user.id, [product.id])
    return ProductOut.model_validate(product).model_copy(
        update={"is_favorite": product.id in fav}
    )


# ---------- CRUD (только admin) ----------

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """UC-21. Создание продукта в справочнике."""
    await _ensure_category_exists(db, payload.category_id)

    product = Product(
        product_name=payload.product_name,
        category_id=payload.category_id,
        image_path=payload.image_path,
        calories=payload.calories,
        proteins=payload.proteins,
        fats=payload.fats,
        carbs=payload.carbs,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    UC-21. Изменение продукта. Прошлые записи дневника не меняются (БП-2):
    в diary_entries хранится snapshot КБЖУ и item_name.
    Изменения автоматически пересчитают КБЖУ рецептов, в которых участвует продукт
    (recipes_nutrition считает по текущим значениям product).
    """
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    if payload.category_id is not None:
        await _ensure_category_exists(db, payload.category_id)

    # Обновляем только присланные поля (PATCH-семантика)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return ProductOut.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_admin: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    UC-21. Удаление продукта из справочника.

    БД: favorites.product_id — ON DELETE CASCADE (удалятся),
    diary_entries.product_id — ON DELETE SET NULL (snapshot сохраняется),
    recipe_ingredients.product_id — ON DELETE RESTRICT. Если продукт используется
    в рецептах, возвращаем 409, пока не решено, каскадно чистить ингредиенты
    или блокировать удаление.
    """
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    used_in_recipes = await db.scalar(
        select(func.count(RecipeIngredient.id))
        .where(RecipeIngredient.product_id == product_id)
    )
    if used_in_recipes:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Product is used in {used_in_recipes} recipe(s); remove it from recipes first",
        )

    await db.delete(product)
    await db.commit()
    return None
