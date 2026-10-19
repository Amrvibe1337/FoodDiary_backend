from __future__ import annotations
 
from typing import TYPE_CHECKING
 
from sqlalchemy import (
    REAL,
    CheckConstraint,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.database import Base
 
if TYPE_CHECKING:
    from .diary import DiaryEntry, Favorite


class Category(Base):
    __tablename__ = "categories"
 
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
 
    products: Mapped[list[Product]] = relationship(back_populates="category")
 
 
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("calories >= 0", name="products_calories_check"),
        CheckConstraint("proteins >= 0", name="products_proteins_check"),
        CheckConstraint("fats >= 0", name="products_fats_check"),
        CheckConstraint("carbs >= 0", name="products_carbs_check"),
    )
 
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", onupdate="NO ACTION", ondelete="NO ACTION"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories: Mapped[float] = mapped_column(REAL, nullable=False)
    proteins: Mapped[float] = mapped_column(REAL, nullable=False)
    fats: Mapped[float] = mapped_column(REAL, nullable=False)
    carbs: Mapped[float] = mapped_column(REAL, nullable=False)
 
    category: Mapped[Category] = relationship(back_populates="products")
    recipe_ingredients: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="product"
    )
    diary_entries: Mapped[list[DiaryEntry]] = relationship(
        back_populates="product", passive_deletes=True
    )
    favorites: Mapped[list[Favorite]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
 
 
class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint(
            "category IN ('массонабор', 'похудение', 'баланс')",
            name="recipes_category_check",
        ),
        CheckConstraint("calories >= 0", name="recipes_calories_check"),
        CheckConstraint("proteins >= 0", name="recipes_proteins_check"),
        CheckConstraint("fats >= 0", name="recipes_fats_check"),
        CheckConstraint("carbs >= 0", name="recipes_carbs_check"),
    )
 
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    recipe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories: Mapped[float] = mapped_column(REAL, nullable=False)
    proteins: Mapped[float] = mapped_column(REAL, nullable=False)
    fats: Mapped[float] = mapped_column(REAL, nullable=False)
    carbs: Mapped[float] = mapped_column(REAL, nullable=False)
 
    steps: Mapped[list[RecipeStep]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecipeStep.step_number",
    )
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", passive_deletes=True
    )
    diary_entries: Mapped[list[DiaryEntry]] = relationship(
        back_populates="recipe", passive_deletes=True
    )
    favorites: Mapped[list[Favorite]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", passive_deletes=True
    )
 
 
class RecipeStep(Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (
        UniqueConstraint("recipe_id", "step_number"),
        CheckConstraint("step_number > 0", name="recipe_steps_step_number_check"),
    )
 
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
 
    recipe: Mapped[Recipe] = relationship(back_populates="steps")
 
 
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "product_id"),
        CheckConstraint("amount_grams > 0", name="recipe_ingredients_amount_check"),
    )
 
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", onupdate="NO ACTION", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", onupdate="NO ACTION", ondelete="RESTRICT"),
        nullable=False,
    )
    amount_grams: Mapped[float] = mapped_column(REAL, nullable=False)
 
    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    product: Mapped[Product] = relationship(back_populates="recipe_ingredients")
 