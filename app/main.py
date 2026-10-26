from fastapi import FastAPI  

from app.routers import favorites, meals, profiles, users

app = FastAPI(title="Food Diary - Дневник питания",
              version="0.1.0",
)
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(meals.router)
app.include_router(favorites.router)

@app.get("/")
async def main():
    """
    Корневой маршрут, подтверждающий, что API работает
    """
    return {"message": "Добро пожаловать в Food Diary"}

