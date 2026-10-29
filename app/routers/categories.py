from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models import Category
from app.models.user import User as UserModel
from app.schemas import CategoryOut


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Справочник категорий продуктов. Нужен для фильтра и админки."""
    rows = await db.scalars(select(Category).order_by(Category.category_name))
    return list(rows)
