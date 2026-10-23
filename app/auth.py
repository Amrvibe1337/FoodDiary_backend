from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User as UserModel
from app.config import SECRET_KEY, ALGORITHM
from app.db_depends import get_async_db

 
# Создаём контекст для хеширования с использованием bcrypt
pwd_context = CryptContext(schemas=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

def hash_password(password: str) -> str:
    """
    Преобразует пароль в хэш с использованием bcrypt
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли введенный пароль сохраненному хешу
    """
    return pwd_context.verify(plain_password, hashed_password)
    
    
def create_access_token(data: dict):
    """
    Создает access-token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
            "exp": expire,
            "token_type": "access",
            })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """
    Создает refresh-токен с длительным сроком действия и token_type="refresh"
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Проверка, что запросы выполняются только авторизованными пользователями
async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_async_db)):
    """
    Проверяет JWT и возвращает пользователя из базы
    iss - issuer - кто выпустил токен
    sub - subject - кому принадлежит токен (уникальный ID юзера)
    aud - audience - для какой аудитории/сервиса предназначен токен
    exp - expire - время истечения срока жизни токена (Unix timestamp)
    iat - issue at - время выпуска токена
    nbf - not before - время, до которого токен еще недействителен
    jti - JWT ID - уникальный идентификатор самого токена
    Пользовательские данные, которые приложение решило передать внутри токена для удобства (чтобы каждый раз не ходить в базу данных): role, email;
    """
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
            )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.scalars(
            select(UserModel).where(UserModel.email == email)
            )
    user = result.first()
    if user is None:
        raise credentials_exception

    return user 


async def get_current_client(current_user: UserModel = Depends(get_current_user)):
    """
    Проверяет, что пользователь имеет роль 'client'.
    """
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only client can perform this action")
    return current_user


async def get_current_admin(current_user: UserModel = Depends(get_current_user)):
    """
    Проверяет, что пользователь имеет роль 'admin'.
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admin can perform this action")
    return current_user


async def get_current_guest(current_user: UserModel = Depends(get_current_user)):
    """
    Проверяет, что пользователь имеет роль 'guest'
    """
    if current_user.role != 'guest':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only guest can perform this action")
    
    return current_user


async def get_current_client_or_admin(current_user: UserModel = Depends(get_current_user)):
    """
    Проверяет, что пользователь имеет роль 'client' или 'admin'
    """
    if current_user.role not in ('client', 'admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only client or admin can perform this action")
    
    return current_user
