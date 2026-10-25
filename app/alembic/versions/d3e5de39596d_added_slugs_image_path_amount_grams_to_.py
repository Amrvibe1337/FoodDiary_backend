"""added slugs, image_path, amount grams to numeric. removed calories, etc from recipes

Revision ID: d3e5de39596d
Revises: 3db6703180b7
Create Date: 2026-10-25 16:01:12.804735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e5de39596d'
down_revision: Union[str, Sequence[str], None] = '3db6703180b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('categories', sa.Column('slug', sa.String(length=50), nullable=True))
    op.execute(
        "UPDATE categories SET slug = CASE category_name "
        "WHEN 'Крупы и макароны' THEN 'grains' "
        "WHEN 'Мясо и рыба' THEN 'meat' "
        "WHEN 'Молочные продукты и яйца' THEN 'dairy' "
        "WHEN 'Овощи' THEN 'vegetables' "
        "WHEN 'Фрукты и ягоды' THEN 'fruits' "
        "WHEN 'Орехи и семена' THEN 'nuts' "
        "WHEN 'Хлеб' THEN 'bread' "
        "WHEN 'Масла и сладкое' THEN 'oils' "
        "END"
    )
    op.alter_column('categories', 'slug', existing_type=sa.String(length=50), nullable=False)
    op.create_unique_constraint('categories_slug_key', 'categories', ['slug'])

    op.drop_constraint('diary_entries_item_consistency_check', 'diary_entries', type_='check')
    op.alter_column('diary_entries', 'amount_grams',
               existing_type=sa.INTEGER(),
               type_=sa.Numeric(precision=8, scale=2),
               existing_nullable=True)
    op.create_check_constraint(
        'diary_entries_item_consistency_check', 'diary_entries',
        "(item_type = 'product' AND recipe_id IS NULL AND amount_grams > 0 AND amount_grams < 5000) "
        "OR (item_type = 'recipe' AND product_id IS NULL AND amount_grams IS NULL)"
    )

    op.add_column('products', sa.Column('image_path', sa.String(length=512), nullable=True))

    op.drop_constraint('recipe_ingredients_amount_check', 'recipe_ingredients', type_='check')
    op.alter_column('recipe_ingredients', 'amount_grams',
               existing_type=sa.REAL(),
               type_=sa.Numeric(precision=8, scale=2),
               existing_nullable=False)
    op.create_check_constraint(
        'recipe_ingredients_amount_check', 'recipe_ingredients',
        'amount_grams > 0 AND amount_grams < 5000'
    )

    op.add_column('recipes', sa.Column('image_path', sa.String(length=512), nullable=True))
    op.drop_constraint('recipes_category_check', 'recipes', type_='check')
    op.execute(
        "UPDATE recipes SET category = CASE category "
        "WHEN 'массонабор' THEN 'mass' "
        "WHEN 'похудение' THEN 'loss' "
        "WHEN 'баланс' THEN 'balance' "
        "ELSE category END"
    )
    op.create_check_constraint(
        'recipes_category_check', 'recipes',
        "category IN ('mass', 'loss', 'balance')"
    )
    op.drop_column('recipes', 'fats')
    op.drop_column('recipes', 'proteins')
    op.drop_column('recipes', 'calories')
    op.drop_column('recipes', 'carbs')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('recipes', sa.Column('carbs', sa.NUMERIC(precision=8, scale=2), autoincrement=False, nullable=False))
    op.add_column('recipes', sa.Column('calories', sa.NUMERIC(precision=8, scale=2), autoincrement=False, nullable=False))
    op.add_column('recipes', sa.Column('proteins', sa.NUMERIC(precision=8, scale=2), autoincrement=False, nullable=False))
    op.add_column('recipes', sa.Column('fats', sa.NUMERIC(precision=8, scale=2), autoincrement=False, nullable=False))
    op.drop_constraint('recipes_category_check', 'recipes', type_='check')
    op.execute(
        "UPDATE recipes SET category = CASE category "
        "WHEN 'mass' THEN 'массонабор' "
        "WHEN 'loss' THEN 'похудение' "
        "WHEN 'balance' THEN 'баланс' "
        "ELSE category END"
    )
    op.create_check_constraint(
        'recipes_category_check', 'recipes',
        "category IN ('массонабор', 'похудение', 'баланс')"
    )
    op.drop_column('recipes', 'image_path')

    op.drop_constraint('recipe_ingredients_amount_check', 'recipe_ingredients', type_='check')
    op.alter_column('recipe_ingredients', 'amount_grams',
               existing_type=sa.Numeric(precision=8, scale=2),
               type_=sa.REAL(),
               existing_nullable=False)
    op.create_check_constraint(
        'recipe_ingredients_amount_check', 'recipe_ingredients',
        'amount_grams > 0'
    )

    op.drop_column('products', 'image_path')

    op.drop_constraint('diary_entries_item_consistency_check', 'diary_entries', type_='check')
    op.alter_column('diary_entries', 'amount_grams',
               existing_type=sa.Numeric(precision=8, scale=2),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.create_check_constraint(
        'diary_entries_item_consistency_check', 'diary_entries',
        "(item_type = 'product' AND recipe_id IS NULL AND amount_grams BETWEEN 1 AND 5000) "
        "OR (item_type = 'recipe' AND product_id IS NULL AND amount_grams IS NULL)"
    )

    op.drop_constraint('categories_slug_key', 'categories', type_='unique')
    op.drop_column('categories', 'slug')
