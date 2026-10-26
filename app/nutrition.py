from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, RecipeIngredient

HUNDRED = Decimal("100")
CENT = Decimal("0.01")


def round_nutrition(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


async def recipes_nutrition(
    session: AsyncSession, recipe_ids: Sequence[int]
) -> dict[int, tuple[Decimal, Decimal, Decimal, Decimal]]:
    if not recipe_ids:
        return {}

    rows = await session.execute(
        select(
            RecipeIngredient.recipe_id,
            func.sum(RecipeIngredient.amount_grams * Product.calories / HUNDRED),
            func.sum(RecipeIngredient.amount_grams * Product.proteins / HUNDRED),
            func.sum(RecipeIngredient.amount_grams * Product.fats / HUNDRED),
            func.sum(RecipeIngredient.amount_grams * Product.carbs / HUNDRED),
        )
        .join(Product, Product.id == RecipeIngredient.product_id)
        .where(RecipeIngredient.recipe_id.in_(recipe_ids))
        .group_by(RecipeIngredient.recipe_id)
    )

    return {
        recipe_id: (
            round_nutrition(calories),
            round_nutrition(proteins),
            round_nutrition(fats),
            round_nutrition(carbs),
        )
        for recipe_id, calories, proteins, fats, carbs in rows.all()
    }
