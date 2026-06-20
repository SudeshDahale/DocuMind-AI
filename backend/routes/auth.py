import uuid
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db, User, APIKey, QueryHistory, Document
from core.security import (
    hash_password, verify_password, create_token,
    encrypt_api_key, decrypt_api_key,
    get_current_user, get_user_openai_key
)
import json

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class APIKeyRequest(BaseModel):
    api_key: str


@router.post("/signup")
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=str(uuid.uuid4()),
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        created_at=time.time(),
    )
    db.add(user)
    await db.commit()
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


# --- API Key Management ---

@router.post("/apikey")
async def save_api_key(
    body: APIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.api_key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Invalid OpenAI API key format")
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    encrypted = encrypt_api_key(body.api_key)
    if existing:
        existing.encrypted_key = encrypted
    else:
        db.add(APIKey(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            encrypted_key=encrypted,
            created_at=time.time(),
            total_calls=0,
        ))
    await db.commit()
    return {"message": "API key saved successfully"}


@router.get("/apikey/status")
async def api_key_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    key_row = result.scalar_one_or_none()
    if not key_row:
        return {"has_key": False, "total_calls": 0}
    decrypted = decrypt_api_key(key_row.encrypted_key)
    masked = decrypted[:7] + "..." + decrypted[-4:]
    return {"has_key": True, "masked_key": masked, "total_calls": key_row.total_calls}


@router.delete("/apikey")
async def delete_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    key_row = result.scalar_one_or_none()
    if key_row:
        await db.delete(key_row)
        await db.commit()
    return {"message": "API key removed"}


# --- Query History ---

@router.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QueryHistory)
        .where(QueryHistory.user_id == current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return {"history": [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "doc_ids": json.loads(r.doc_ids),
            "created_at": r.created_at,
        } for r in rows
    ]}