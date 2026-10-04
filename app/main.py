from fastapi import FastAPI  

app = FastAPI(title="Food Diary - Дневник питания",
              version="0.1.0",
)

@app.get("/")
async def main():
    """
    Корневой маршрут, подтверждающий, что API работает
    """
    return {"message": "Добро пожаловать в Food Diary"}

