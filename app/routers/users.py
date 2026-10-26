from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import User as UserModel
from app.schemas import UserCreate, User as UserSchema, RefreshTokenRequest
from app.db_depends import get_async_db
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user

import jwt
from app.config import SECRET_KEY, ALGORITHM


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Регистрирует нового пользователя с ролью 'user' или 'admin'.
    """
    # Проверка уникальности email
    result = await db.scalars(select(UserModel).where(UserModel.email == user.email))
    if result.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Email already registered")
    
    # Создание объекта пользователя с хешированным паролем
    db_user = UserModel(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
        role="user"
    )

    # Добавление в сессию и сохранение в базе
    db.add(db_user)
    await db.commit()
    return db_user


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """
    result = await db.scalars(
        select(UserModel).where(UserModel.email == form_data.username)
    )
    user = result.first()   # Нашли чела в таблице UserModel по почте из формы
    # Если нет чела с такой почтой или введенный пароль не совпадает, то ошибка.
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Иначе возвращаем пользователю токены
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": user.role, "id": user.id})    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh-token")
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Обновляет refresh-token, принимая старый refresh-token в теле запроса.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        # Проверяем, что токен действительно refresh
        if email is None or token_type != "refresh":
            raise credentials_exception
        
    except jwt.ExpiredSignatureError:
        # refresh-токен истёк
        raise credentials_exception
    
    except jwt.PyJWTError:
        # подпись неверна или токен повреждён
        raise credentials_exception
    
    # Проверяем, что пользователь существует и активен
    result = await db.scalars(
        select(UserModel).where(UserModel.email == email)
    )
    user = result.first()
    if user is None:
        raise credentials_exception
    
    # Генерируем новый refresh-token 
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.email, "role": user.role, "id": user.id
    })
    
    return {
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
    

@router.post("/access-token")
async def new_access_token(body: RefreshTokenRequest,
                           db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает продлённый access-token по refresh токену
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    rfrsh_tkn = body.refresh_token

    try:
        payload = jwt.decode(rfrsh_tkn, SECRET_KEY,  algorithms=[ALGORITHM])

        email: str | None = payload.get("sub")
        token_type: str | None =  payload.get("token_type")

        if email is None or token_type != "refresh":
            raise credentials_exception
        
    except jwt.ExpiredSignatureError:
        # refresh-токен истёк
        raise credentials_exception
    
    except jwt.PyJWTError:
        # подпись неверна или токен повреждён
        raise credentials_exception
    
    # Проверяем, что пользователь существует и активен
    result = await db.scalars(select(UserModel).where(UserModel.email == email))
    user = result.first()
    if user is None:
        raise credentials_exception
    
    # Пользователь существует и refresh-токен валиден
    # Генерируем новый access_token
    new_access = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    
    return {
        "access_token": new_access,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Завершает сессию пользователя.

    get_current_user уже проверил подпись, срок действия access-токена
    и существование пользователя в БД (иначе вернул бы 401).

    В текущей архитектуре (stateless JWT) сервер не хранит сессии,
    поэтому эндпоинт только подтверждает валидность токена и возвращает 204.
    Клиент после успешного ответа должен удалить access_token и
    refresh_token из localStorage.
    """
    # Ничего не сохраняем: JWT stateless.
    # Для серверного отзыва токенов нужен blacklist — см. заметку ниже.
    return None
