from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .food import Product, Recipe
    from .user import User


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        CheckConstraint("item_type IN ('product', 'recipe')", name="diary_item_type_check"),
        CheckConstraint("calories >= 0", name="diary_calories_check"),
        CheckConstraint("proteins >= 0", name="diary_proteins_check"),
        CheckConstraint("fats >= 0", name="diary_fats_check"),
        CheckConstraint("carbs >= 0", name="diary_carbs_check"),
        CheckConstraint(
            "(item_type = 'product' AND recipe_id IS NULL AND amount_grams > 0 AND amount_grams < 5000) "
            "OR (item_type = 'recipe' AND product_id IS NULL AND amount_grams IS NULL)",
            name="diary_entries_item_consistency_check",
        ),
        Index("diary_entries_user_date_idx", "user_id", "date"),
        Index("diary_entries_product_id_idx", "product_id"),
        Index("diary_entries_recipe_id_idx", "recipe_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(String(10), nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", onupdate="NO ACTION", ondelete="SET NULL"),
        nullable=True,
    )
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id", onupdate="NO ACTION", ondelete="SET NULL"),
        nullable=True,
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_grams: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    calories: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    proteins: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fats: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    date: Mapped[dt.date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )

    user: Mapped[User] = relationship(back_populates="diary_entries")
    product: Mapped[Product | None] = relationship(back_populates="diary_entries")
    recipe: Mapped[Recipe | None] = relationship(back_populates="diary_entries")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id"),
        UniqueConstraint("user_id", "recipe_id"),
        CheckConstraint(
            "(product_id IS NULL) <> (recipe_id IS NULL)",
            name="favorites_product_xor_recipe_check",
        ),
        Index("favorites_product_id_idx", "product_id"),
        Index("favorites_recipe_id_idx", "recipe_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=True,
    )
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="favorites")
    product: Mapped[Product | None] = relationship(back_populates="favorites")
    recipe: Mapped[Recipe | None] = relationship(back_populates="favorites")
