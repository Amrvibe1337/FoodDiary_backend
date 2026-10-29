from fastapi import status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Favorite

# ---------- Хелперы ----------

async def _favorite_ids(db: AsyncSession, user_id: int, product_ids: list[int]) -> set[int]:
    if not product_ids:
        return set()
    rows = await db.scalars(
        select(Favorite.product_id)
        .where(Favorite.user_id == user_id, Favorite.product_id.in_(product_ids))
    )
    return {pid for pid in rows if pid is not None}


async def _ensure_category_exists(db: AsyncSession, category_id: int) -> None:
    if await db.get(Category, category_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
