from fastapi import FastAPI  
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import favorites, meals, posts, profiles, users, recipes, categories, products

app = FastAPI(title="Food Diary - Дневник питания",
              version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,       # список, не "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(meals.router)
app.include_router(favorites.router)
app.include_router(posts.router)
app.include_router(recipes.router)
app.include_router(products.router)
app.include_router(categories.router)

@app.get("/")
async def main():
    """
    Корневой маршрут, подтверждающий, что API работает
    """
    return {"message": "Добро пожаловать в Food Diary"}

