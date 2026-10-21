import asyncio
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

# Импортируем асинхронную фабрику сессий
from app.database import async_session_maker
# Импортируем модели
from app.models import (
    Category, Product, Recipe, RecipeIngredient, 
    RecipeStep, User, Post, Comment, 
    DiaryEntry, Favorite, PostLike
)

async def test_database():
    # Открываем асинхронную сессию через контекстный менеджер
    async with async_session_maker() as db:
        print("Начинаем асинхронное тестирование базы данных...\n")

        # ==========================================
        # ЧАСТЬ 1: ВСТАВКА ВАЛИДНЫХ ДАННЫХ (Happy Path)
        # ==========================================
        try:
            print("1. Вставляем валидные данные...")
            
            # Категория и Продукт
            cat = Category(category_name="Мясо и птица")
            db.add(cat)
            await db.flush() # Получаем cat.id

            prod = Product(
                category_id=cat.id, product_name="Куриная грудка", 
                calories=165.0, proteins=31.0, fats=3.6, carbs=0.0
            )
            db.add(prod)
            await db.flush()

            # Юзер
            user = User(
                email="test_async@example.com", password_hash="hash123", name="Тестовый Юзер"
            )
            db.add(user)
            await db.flush()

            # Рецепт и его составляющие
            recipe = Recipe(
                recipe_name="Курица на пару", category="похудение",
                description="Просто и полезно", instructions="1. Помыть. 2. Готовить.",
                calories=200.0, proteins=35.0, fats=4.0, carbs=0.0
            )
            db.add(recipe)
            await db.flush()

            ingredient = RecipeIngredient(
                recipe_id=recipe.id, product_id=prod.id, amount_grams=150.0
            )
            db.add(ingredient)

            step = RecipeStep(
                recipe_id=recipe.id, step_number=1, description="Включить пароварку"
            )
            db.add(step)

            # Пост, коммент, лайк
            post = Post(user_id=user.id, content="Привет, я на диете!")
            db.add(post)
            await db.flush()

            comment = Comment(user_id=user.id, post_id=post.id, content="Молодец!")
            db.add(comment)

            like = PostLike(user_id=user.id, post_id=post.id)
            db.add(like)

            # Запись в дневник (Продукт)
            diary_prod = DiaryEntry(
                user_id=user.id, item_type="product", product_id=prod.id,
                item_name="Куриная грудка", amount_grams=200,
                calories=330.0, proteins=62.0, fats=7.2, carbs=0.0, date=date.today()
            )
            db.add(diary_prod)

            # Избранное
            fav = Favorite(user_id=user.id, recipe_id=recipe.id)
            db.add(fav)

            await db.commit()
            print(f"✅ Валидные данные успешно добавлены! (ID юзера: {user.id}, ID продукта: {prod.id})\n")

        except Exception as e:
            await db.rollback()
            print(f"❌ ОШИБКА при вставке валидных данных: {e}\n")
            return

        # ==========================================
        # ЧАСТЬ 2: ПРОВЕРКА ОГРАНИЧЕНИЙ (Constraints)
        # ==========================================
        print("2. Начинаем проверку ограничений (ожидаем ошибки)...")

        # Тест 1: Отрицательные калории
        try:
            bad_prod = Product(category_id=cat.id, product_name="Плохой продукт", calories=-10, proteins=0, fats=0, carbs=0)
            db.add(bad_prod)
            await db.commit()
            print("❌ Тест 1 ПРОВАЛЕН: Отрицательные калории разрешены!")
        except IntegrityError:
            await db.rollback()
            print("✅ Тест 1 (Отрицательные калории): БД не дала сохранить. ОК.")

        # Тест 2: Слишком длинный пост (>500 символов)
        try:
            long_post = Post(user_id=user.id, content="А" * 501)
            db.add(long_post)
            await db.commit()
            print("❌ Тест 2 ПРОВАЛЕН: Длинный пост (501 символ) разрешен!")
        except IntegrityError:
            await db.rollback()
            print("✅ Тест 2 (Длина поста > 500): БД не дала сохранить. ОК.")

        # Тест 3: Дубликат категории
        try:
            dup_cat = Category(category_name="Мясо и птица")
            db.add(dup_cat)
            await db.commit()
            print("❌ Тест 3 ПРОВАЛЕН: Дубликат категории разрешен!")
        except IntegrityError:
            await db.rollback()
            print("✅ Тест 3 (Уникальность категории): БД не дала сохранить. ОК.")

        # Тест 4: Логика дневника (нельзя и product_id, и recipe_id)
        try:
            bad_diary = DiaryEntry(
                user_id=user.id, item_type="product", product_id=prod.id, recipe_id=recipe.id,
                item_name="Ошибка", amount_grams=100, calories=100, proteins=0, fats=0, carbs=0
            )
            db.add(bad_diary)
            await db.commit()
            print("❌ Тест 4 ПРОВАЛЕН: Дневник принял и продукт, и рецепт!")
        except IntegrityError:
            await db.rollback()
            print("✅ Тест 4 (Дневник XOR): БД не дала сохранить. ОК.")

        # ==========================================
        # ЧАСТЬ 3: ПРОВЕРКА КАСКАДНОГО УДАЛЕНИЯ
        # ==========================================
        print("\n3. Проверяем каскадное удаление (Удаляем юзера)...")
        try:
            user_id_to_check = user.id
            prod_id_to_check = prod.id
            
            # Удаляем юзера
            await db.delete(user)
            await db.commit()
            print("✅ Юзер удален.")

            # Проверяем посты (используем select и scalar для async)
            posts_count = await db.scalar(
                select(func.count()).select_from(Post).where(Post.user_id == user_id_to_check)
            )
            if posts_count == 0:
                print("✅ Каскад работает: Посты юзера удалены.")
            else:
                print(f"❌ Каскад сломан: Осталось {posts_count} постов!")

            # Проверяем, что продукт НЕ удалился
            prod_exists = await db.scalar(
                select(Product).where(Product.id == prod_id_to_check)
            )
            if prod_exists:
                print("✅ Продукт остался в базе (правильно, он общий).")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Ошибка при тестировании каскада: {e}")

    print("\n🏁 Тестирование завершено!")


if __name__ == "__main__":
    # Запускаем асинхронный цикл событий
    asyncio.run(test_database())
