import argparse
import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL
from app.models import Category, Product, Recipe, RecipeIngredient, RecipeStep
from scripts.seed_data import (
    CATEGORIES,
    PRODUCTS,
    PRODUCT_IMAGES,
    RECIPES,
    RECIPE_IMAGES,
    RecipeSeed,
)

RECIPE_CATEGORIES = {"mass", "loss", "balance"}
Nutrition = dict[str, tuple[Decimal, Decimal, Decimal, Decimal]]
MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"


def validate() -> None:
    category_slugs = {category.slug for category in CATEGORIES}
    if len(category_slugs) != len(CATEGORIES):
        raise ValueError("дублируются слаги категорий")

    product_names = [product.name for product in PRODUCTS]
    if len(set(product_names)) != len(product_names):
        raise ValueError("дублируются названия продуктов")

    for product in PRODUCTS:
        if product.category not in category_slugs:
            raise ValueError(
                f"продукт «{product.name}»: неизвестная категория «{product.category}»"
            )
        for value in (product.calories, product.proteins, product.fats, product.carbs):
            if Decimal(value) < 0:
                raise ValueError(f"продукт «{product.name}»: отрицательное КБЖУ")

    recipe_names = [recipe.name for recipe in RECIPES]
    if len(set(recipe_names)) != len(recipe_names):
        raise ValueError("дублируются названия рецептов")

    known_products = set(product_names)
    for recipe in RECIPES:
        if recipe.category not in RECIPE_CATEGORIES:
            raise ValueError(
                f"рецепт «{recipe.name}»: неизвестная категория «{recipe.category}»"
            )
        if not recipe.steps:
            raise ValueError(f"рецепт «{recipe.name}»: нет шагов")
        if not recipe.ingredients:
            raise ValueError(f"рецепт «{recipe.name}»: нет ингредиентов")

        ingredient_products = [product for product, _ in recipe.ingredients]
        if len(set(ingredient_products)) != len(ingredient_products):
            raise ValueError(f"рецепт «{recipe.name}»: продукт повторяется в ингредиентах")

        for product_name, grams in recipe.ingredients:
            if product_name not in known_products:
                raise ValueError(
                    f"рецепт «{recipe.name}»: неизвестный продукт «{product_name}»"
                )
            amount = Decimal(grams)
            if not Decimal("0") < amount < Decimal("5000"):
                raise ValueError(
                    f"рецепт «{recipe.name}»: недопустимая граммовка {grams}"
                )

    missing_product_images = [
        product.name for product in PRODUCTS if product.name not in PRODUCT_IMAGES
    ]
    if missing_product_images:
        raise ValueError(f"нет пути к фото для продуктов: {missing_product_images}")

    missing_recipe_images = [
        recipe.name for recipe in RECIPES if recipe.name not in RECIPE_IMAGES
    ]
    if missing_recipe_images:
        raise ValueError(f"нет пути к фото для рецептов: {missing_recipe_images}")


def resolve_image(mapping: dict[str, str], name: str) -> str | None:
    path = mapping.get(name)
    if path is None or not (MEDIA_DIR / path).exists():
        return None
    return path


def build_nutrition(existing: dict[str, Product]) -> Nutrition:
    nutrition: Nutrition = {}
    for product in PRODUCTS:
        found = existing.get(product.name)
        if found is not None:
            nutrition[product.name] = (
                found.calories,
                found.proteins,
                found.fats,
                found.carbs,
            )
        else:
            nutrition[product.name] = (
                Decimal(product.calories),
                Decimal(product.proteins),
                Decimal(product.fats),
                Decimal(product.carbs),
            )
    return nutrition


def recipe_totals(
    recipe: RecipeSeed, nutrition: Nutrition
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    calories = proteins = fats = carbs = Decimal("0")
    for product_name, grams in recipe.ingredients:
        values = nutrition[product_name]
        factor = Decimal(grams) / Decimal("100")
        calories += values[0] * factor
        proteins += values[1] * factor
        fats += values[2] * factor
        carbs += values[3] * factor
    return calories, proteins, fats, carbs


def print_recipe_totals(nutrition: Nutrition) -> None:
    print()
    print(f"{'Рецепт':<36} {'Ккал':>7} {'Б':>6} {'Ж':>6} {'У':>6}")
    for recipe in RECIPES:
        calories, proteins, fats, carbs = recipe_totals(recipe, nutrition)
        print(
            f"{recipe.name:<36} {calories:>7.1f} {proteins:>6.1f} "
            f"{fats:>6.1f} {carbs:>6.1f}"
        )


async def load_categories(session: AsyncSession) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for seed_category in CATEGORIES:
        category = await session.scalar(
            select(Category).where(Category.slug == seed_category.slug)
        )
        if category is not None:
            categories[seed_category.slug] = category
    return categories


async def load_products(session: AsyncSession) -> dict[str, Product]:
    products: dict[str, Product] = {}
    for seed_product in PRODUCTS:
        product = await session.scalar(
            select(Product).where(Product.product_name == seed_product.name)
        )
        if product is not None:
            products[seed_product.name] = product
    return products


async def load_recipes(session: AsyncSession) -> set[str]:
    recipes: set[str] = set()
    for seed_recipe in RECIPES:
        recipe_id = await session.scalar(
            select(Recipe.id).where(Recipe.recipe_name == seed_recipe.name)
        )
        if recipe_id is not None:
            recipes.add(seed_recipe.name)
    return recipes


async def apply_seed(
    session: AsyncSession,
    categories: dict[str, Category],
    products: dict[str, Product],
    recipes: set[str],
) -> dict[str, list[int]]:
    stats = {"categories": [0, 0], "products": [0, 0], "recipes": [0, 0]}

    for seed_category in CATEGORIES:
        if seed_category.slug in categories:
            stats["categories"][1] += 1
            continue
        category = Category(slug=seed_category.slug, category_name=seed_category.name)
        session.add(category)
        categories[seed_category.slug] = category
        stats["categories"][0] += 1
    await session.flush()

    for seed_product in PRODUCTS:
        if seed_product.name in products:
            stats["products"][1] += 1
            continue
        product = Product(
            category_id=categories[seed_product.category].id,
            product_name=seed_product.name,
            image_path=resolve_image(PRODUCT_IMAGES, seed_product.name),
            calories=Decimal(seed_product.calories),
            proteins=Decimal(seed_product.proteins),
            fats=Decimal(seed_product.fats),
            carbs=Decimal(seed_product.carbs),
        )
        session.add(product)
        products[seed_product.name] = product
        stats["products"][0] += 1
    await session.flush()

    for seed_recipe in RECIPES:
        if seed_recipe.name in recipes:
            stats["recipes"][1] += 1
            continue

        recipe = Recipe(
            recipe_name=seed_recipe.name,
            category=seed_recipe.category,
            description=seed_recipe.description,
            image_path=resolve_image(RECIPE_IMAGES, seed_recipe.name),
        )
        session.add(recipe)
        await session.flush()

        for number, description in enumerate(seed_recipe.steps, start=1):
            session.add(
                RecipeStep(
                    recipe_id=recipe.id,
                    step_number=number,
                    description=description,
                )
            )

        for product_name, grams in seed_recipe.ingredients:
            session.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    product_id=products[product_name].id,
                    amount_grams=Decimal(grams),
                )
            )

        stats["recipes"][0] += 1
    await session.flush()

    return stats


async def main(dry_run: bool) -> None:
    validate()

    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            categories = await load_categories(session)
            products = await load_products(session)
            recipes = await load_recipes(session)

            print_recipe_totals(build_nutrition(products))

            if dry_run:
                stats = {
                    "categories": [len(CATEGORIES) - len(categories), len(categories)],
                    "products": [len(PRODUCTS) - len(products), len(products)],
                    "recipes": [len(RECIPES) - len(recipes), len(recipes)],
                }
            else:
                try:
                    stats = await apply_seed(session, categories, products, recipes)
                except Exception:
                    await session.rollback()
                    raise
                await session.commit()
    finally:
        await engine.dispose()

    print()
    for key, label in (
        ("categories", "Категории"),
        ("products", "Продукты"),
        ("recipes", "Рецепты"),
    ):
        created, skipped = stats[key]
        print(f"{label}: создано {created}, пропущено {skipped}")

    attached_products = sum(
        resolve_image(PRODUCT_IMAGES, name) is not None for name in PRODUCT_IMAGES
    )
    attached_recipes = sum(
        resolve_image(RECIPE_IMAGES, name) is not None for name in RECIPE_IMAGES
    )
    print(f"Фото продуктов: {attached_products} из {len(PRODUCT_IMAGES)}")
    print(f"Фото рецептов: {attached_recipes} из {len(RECIPE_IMAGES)}")

    missing = [
        name
        for name in PRODUCT_IMAGES
        if resolve_image(PRODUCT_IMAGES, name) is None
    ] + [
        name
        for name in RECIPE_IMAGES
        if resolve_image(RECIPE_IMAGES, name) is None
    ]
    if missing:
        print("Файлы не найдены:", ", ".join(missing))

    if dry_run:
        print("Режим проверки: в базу ничего не записано")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Наполняет каталог продуктами и рецептами"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="проверить данные и показать расчёт без записи в БД",
    )
    arguments = parser.parse_args()

    try:
        asyncio.run(main(arguments.dry_run))
    except ValueError as error:
        print(f"Ошибка данных: {error}")
        raise SystemExit(1)
