from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models import Comment, Post, PostLike
from app.models.user import User as UserModel
from app.schemas import CommentCreate, CommentOut, LikeOut, PostCreate, PostOut

router = APIRouter(prefix="/posts", tags=["posts"])

POST_MAX_LENGTH = 500
COMMENT_MAX_LENGTH = 300


@router.get("", response_model=list[PostOut])
async def list_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Лента постов: новые сверху. Автор, количество лайков и комментариев,
    а также признак лайка текущего пользователя приходят сразу.
    """
    rows = (
        await db.execute(
            select(Post, UserModel.name)
            .join(UserModel, UserModel.id == Post.user_id)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    post_ids = [post.id for post, _ in rows]
    likes_counts: dict[int, int] = {}
    comments_counts: dict[int, int] = {}
    liked_ids: set[int] = set()

    if post_ids:
        likes_counts = {
            post_id: total
            for post_id, total in (
                await db.execute(
                    select(PostLike.post_id, func.count(PostLike.id))
                    .where(PostLike.post_id.in_(post_ids))
                    .group_by(PostLike.post_id)
                )
            ).all()
        }
        comments_counts = {
            post_id: total
            for post_id, total in (
                await db.execute(
                    select(Comment.post_id, func.count(Comment.id))
                    .where(Comment.post_id.in_(post_ids))
                    .group_by(Comment.post_id)
                )
            ).all()
        }
        liked_ids = set(
            await db.scalars(
                select(PostLike.post_id).where(
                    PostLike.post_id.in_(post_ids),
                    PostLike.user_id == current_user.id,
                )
            )
        )

    return [
        PostOut(
            id=post.id,
            user_id=post.user_id,
            author_name=author_name,
            content=post.content,
            created_at=post.created_at,
            likes_count=likes_counts.get(post.id, 0),
            liked=post.id in liked_ids,
            comments_count=comments_counts.get(post.id, 0),
        )
        for post, author_name in rows
    ]


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Создаёт пост. Текст обрезается, длина — от 1 до 500 символов.
    """
    content = payload.content.strip()
    if not content or len(content) > POST_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post content must be from 1 to 500 characters",
        )

    post = Post(user_id=current_user.id, content=content)
    db.add(post)
    await db.commit()

    return PostOut(
        id=post.id,
        user_id=post.user_id,
        author_name=current_user.name,
        content=post.content,
        created_at=post.created_at,
        likes_count=0,
        liked=False,
        comments_count=0,
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Удаляет пост. Доступно автору или администратору.
    """
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    _ensure_owner_or_admin(current_user, post.user_id)

    await db.delete(post)
    await db.commit()
    return None


@router.put("/{post_id}/like", response_model=LikeOut)
async def like_post(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Ставит лайк. Повторный вызов не создаёт второй лайк.
    """
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    existing = await db.scalar(
        select(PostLike.id).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id,
        )
    )
    if existing is None:
        db.add(PostLike(post_id=post_id, user_id=current_user.id))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()

    return LikeOut(liked=True, likes_count=await _likes_count(db, post_id))


@router.delete("/{post_id}/like", response_model=LikeOut)
async def unlike_post(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Снимает лайк. Если лайка не было, ничего не меняет.
    """
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    like = await db.scalar(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id,
        )
    )
    if like is not None:
        await db.delete(like)
        await db.commit()

    return LikeOut(liked=False, likes_count=await _likes_count(db, post_id))


@router.get("/{post_id}/comments", response_model=list[CommentOut])
async def list_comments(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Комментарии поста по порядку добавления.
    """
    if await db.get(Post, post_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    rows = (
        await db.execute(
            select(Comment, UserModel.name)
            .join(UserModel, UserModel.id == Comment.user_id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.id)
        )
    ).all()

    return [
        CommentOut(
            id=comment.id,
            post_id=comment.post_id,
            user_id=comment.user_id,
            author_name=author_name,
            content=comment.content,
            created_at=comment.created_at,
        )
        for comment, author_name in rows
    ]


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: int,
    payload: CommentCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Добавляет комментарий. Текст обрезается, длина — от 1 до 300 символов.
    """
    if await db.get(Post, post_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    content = payload.content.strip()
    if not content or len(content) > COMMENT_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content must be from 1 to 300 characters",
        )

    comment = Comment(post_id=post_id, user_id=current_user.id, content=content)
    db.add(comment)
    await db.commit()

    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        author_name=current_user.name,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Удаляет комментарий поста. Доступно автору комментария или администратору.
    """
    comment = await db.scalar(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        )
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    _ensure_owner_or_admin(current_user, comment.user_id)

    await db.delete(comment)
    await db.commit()
    return None


def _ensure_owner_or_admin(user: UserModel, owner_id: int) -> None:
    if user.id != owner_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough rights",
        )


async def _likes_count(db: AsyncSession, post_id: int) -> int:
    total = await db.scalar(
        select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
    )
    return total or 0
