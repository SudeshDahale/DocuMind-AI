import uuid, time, json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db, User, APIKey, QueryHistory, Document, Workspace
from core.security import (
    hash_password, verify_password, create_token,
    encrypt_api_key, decrypt_api_key,
    get_current_user, get_user_openai_key,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class APIKeyRequest(BaseModel):
    api_key: str

class TokenLimitRequest(BaseModel):
    token_limit: int   # 0 = unlimited

class WorkspaceSaveRequest(BaseModel):
    workspaces: list   # [{id, name, docs:[{docId, fileName}]}]


# ── Auth ──────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=str(uuid.uuid4()), email=body.email.lower(),
        hashed_password=hash_password(body.password), created_at=time.time(),
    )
    db.add(user)
    await db.commit()
    return {"token": create_token(user.id), "user": {"id": user.id, "email": user.email}}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user.id), "user": {"id": user.id, "email": user.email}}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


# ── API Key ───────────────────────────────────────────────────────────────

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
            id=str(uuid.uuid4()), user_id=current_user.id,
            encrypted_key=encrypted, created_at=time.time(),
            total_calls=0, tokens_used=0, token_limit=0,
        ))
    await db.commit()
    return {"message": "API key saved successfully"}


@router.get("/apikey/status")
async def api_key_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    row = result.scalar_one_or_none()
    if not row:
        return {"has_key": False, "total_calls": 0, "tokens_used": 0, "token_limit": 0}
    decrypted = decrypt_api_key(row.encrypted_key)
    masked = decrypted[:7] + "..." + decrypted[-4:]
    return {
        "has_key": True,
        "masked_key": masked,
        "total_calls": row.total_calls,
        "tokens_used": row.tokens_used,
        "token_limit": row.token_limit,
    }


@router.delete("/apikey")
async def delete_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return {"message": "API key removed"}


@router.post("/apikey/limit")
async def set_token_limit(
    body: TokenLimitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No API key found")
    row.token_limit = max(0, body.token_limit)
    await db.commit()
    return {"message": "Token limit updated", "token_limit": row.token_limit}


# ── Workspace persistence ─────────────────────────────────────────────────

@router.post("/workspaces/save")
async def save_workspaces(
    body: WorkspaceSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Upsert workspaces
    incoming_ws_ids = set()
    for ws in body.workspaces:
        incoming_ws_ids.add(ws["id"])
        result = await db.execute(select(Workspace).where(Workspace.id == ws["id"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = ws["name"]
        else:
            db.add(Workspace(
                id=ws["id"], user_id=current_user.id,
                name=ws["name"], created_at=time.time(),
            ))
        # Upsert docs for this workspace
        incoming_doc_ids = set()
        for doc in ws.get("docs", []):
            incoming_doc_ids.add(doc["docId"])
            result2 = await db.execute(select(Document).where(Document.doc_id == doc["docId"]))
            existing_doc = result2.scalar_one_or_none()
            if existing_doc:
                existing_doc.workspace_id = ws["id"]
                existing_doc.file_name = doc["fileName"]
            else:
                db.add(Document(
                    doc_id=doc["docId"], user_id=current_user.id,
                    workspace_id=ws["id"], file_name=doc["fileName"],
                    uploaded_at=time.time(),
                ))

    await db.commit()
    return {"message": "Workspaces saved"}


@router.get("/workspaces/load")
async def load_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import os
    CHUNK_DIR = "storage/chunks"
    INDEX_DIR = "storage/indexes"

    ws_result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id)
    )
    workspaces = ws_result.scalars().all()

    output = []
    for ws in workspaces:
        doc_result = await db.execute(
            select(Document).where(
                Document.user_id == current_user.id,
                Document.workspace_id == ws.id,
            )
        )
        docs = doc_result.scalars().all()
        # Only include docs whose chunks+index still exist on disk
        valid_docs = []
        for doc in docs:
            chunk_ok = os.path.exists(f"{CHUNK_DIR}/{doc.doc_id}.json")
            index_ok = os.path.exists(f"{INDEX_DIR}/{doc.doc_id}.index")
            if chunk_ok and index_ok:
                valid_docs.append({"docId": doc.doc_id, "fileName": doc.file_name})
        output.append({
            "id": ws.id,
            "name": ws.name,
            "docs": valid_docs,
        })

    return {"workspaces": output}


# ── Query History ─────────────────────────────────────────────────────────

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
        {"id": r.id, "question": r.question, "answer": r.answer,
         "doc_ids": json.loads(r.doc_ids), "created_at": r.created_at}
        for r in rows
    ]}