from datetime import date
from sqlalchemy import String, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class MealType(Base):
    __tablename__ = "meal_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # тип приема пищи (по ТЗ необязательный, может быть None)
    meal_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("meal_types.id"), 
        nullable=True
    )
    
    # либо продукт, либо рецепт (одно из них заполнено, второе None)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), 
        nullable=True
    )
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id"), 
        nullable=True
    )
    
    amount_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # дата приема пищи (по умолчанию текущий день)
    date: Mapped[date] = mapped_column(Date, server_default=func.current_date(), nullable=False)


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # звездочка ставится ЛИБО на продукт, ЛИБО на рецепт
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), 
        nullable=True
    )
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id"), 
        nullable=True
    )