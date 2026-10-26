from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models.user import User as UserModel
from app.models.diary import DiaryEntry, Favorite
from app.schemas import ProfileOut, ProfileStats, ProfileUpdate


# Без prefix: пути /profile и /account — на корне, как в п. 6 ТЗ
router = APIRouter(tags=["profile"])


async def _build_profile(user: UserModel, db: AsyncSession) -> ProfileOut:
    """Собирает профиль + статистику тремя агрегатами."""
    entries_count = await db.scalar(
        select(func.count(DiaryEntry.id)).where(DiaryEntry.user_id == user.id)
    )
    days_count = await db.scalar(
        select(func.count(distinct(DiaryEntry.date))).where(DiaryEntry.user_id == user.id)
    )
    favorites_count = await db.scalar(
        select(func.count(Favorite.id)).where(Favorite.user_id == user.id)
    )
    return ProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        stats=ProfileStats(
            diary_entries_count=entries_count or 0,
            diary_days_count=days_count or 0,
            favorites_count=favorites_count or 0,
        ),
    )


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    UC-03. Возвращает профиль: имя, email, дату регистрации и статистику
    (записи в дневнике, дни с записями, количество избранного).
    """
    return await _build_profile(current_user, db)


@router.post("/profile", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    UC-03. Меняет имя пользователя. Email и роль через профиль не меняются.
    """
    new_name = payload.name.strip()
    if len(new_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters",
        )

    if new_name != current_user.name:
        current_user.name = new_name
        await db.commit()
        await db.refresh(current_user)

    return await _build_profile(current_user, db)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    UC-04. Удаляет аккаунт и все связанные данные.
    В схеме БД все FK на users.id объявлены ON DELETE CASCADE
    (diary_entries, favorites, posts, comments, post_likes),
    поэтому достаточно удалить пользователя.
    """
    await db.delete(current_user)
    await db.commit()
    return None
