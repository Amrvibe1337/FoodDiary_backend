Добро пожаловать в учебный проект **FoodDiary**!  
Это backend-приложение для ведения дневника питания, построенное на современном стеке технологий с упором на асинхронность, безопасность и чёткое разграничение прав доступа.

## Описание
Разработали API интернет-магазина на **FastAPI**, используя **асинхронную работу** с базой данных **PostgreSQL** через `AsyncSession`, **SQLAlchemy** и драйвер `asyncpg`. При желании можно контейнеризировать проект через Docker.
Проект охватывает ключевые функциональности для управления пользователями и продуктами с рецептами с возможностями постить и комментировать.

## Стек технологий

- **FastAPI** — современный, быстрый веб-фреймворк для создания API.
- **PostgreSQL** + драйвер **asyncpg** — асинхронная работа с базой данных.
- **SQLAlchemy 2.0** (с поддержкой `AsyncSession`) — асинхронный ORM для взаимодействия с БД.
- **Alembic** — управление миграциями.
- **JWT** — аутентификация и выдача токенов доступа.
- **Pydantic** — валидация данных и работа со схемами.
- **Docker и docker compose** - для контейнеризации сервисов

## Требования

- Python 3.8+
- Virtual environment (рекомендуется)
- OS Linux (Ubuntu)
- Docker engine
## Установка и запуск без Docker и Nginx

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/AmirHan007/fastapi_ecommerce.git
   cd fastapi_ecommerce
   ```
2. Создайте и активируйте виртуальное окружение:
  - Для Linux/Mac:
    ```bash
    source .venv/bin/activate
    ```
  - Для Windows:
    ```bash
    venv\Scripts\Activate.ps1
    ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создайте файл .env на основе .env.example и отредактируйте его:
   ```bash
   cp .env.example .env
   ```
   В .env измените DATABASE_URL и SECRET_KEY.
   Для создания своего `SECRET_KEY` надо выполнить:
   ```bash
   openssl rand -hex 32
   ```
5. Примените миграции:
   ```bash
   alembic upgrade head
   ```
6. Запуск через Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Приложение будет доступно по адресу: http://localhost:8000

## API Документация

FastAPI автоматически генерирует интерактивную документацию:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://0.0.0.0:8000/redoc

## Лицензия

Этот проект предназначен для образовательных и учебных целей.
