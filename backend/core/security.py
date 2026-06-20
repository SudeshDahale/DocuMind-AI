import os
import jwt
import time
import bcrypt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db, User, APIKey

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production-use-long-random-string")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _load_fernet() -> Fernet:
    raw = os.getenv("FERNET_KEY", "").strip()
    if raw:
        try:
            return Fernet(raw.encode() if isinstance(raw, str) else raw)
        except Exception:
            pass
    new_key = Fernet.generate_key()
    print(f"[security] No valid FERNET_KEY found. Generated one for this session.")
    print(f"[security] Add this to your .env to persist it:  FERNET_KEY={new_key.decode()}")
    return Fernet(new_key)


fernet = _load_fernet()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + TOKEN_EXPIRE_SECONDS}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def encrypt_api_key(key: str) -> str:
    return fernet.encrypt(key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    user_id = decode_token(token)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_user_openai_key(user_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(APIKey).where(APIKey.user_id == user_id))
    api_key_row = result.scalar_one_or_none()
    if not api_key_row:
        raise HTTPException(
            status_code=400,
            detail="No OpenAI API key found. Please add your key in settings."
        )
    return decrypt_api_key(api_key_row.encrypted_key)