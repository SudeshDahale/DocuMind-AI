from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.pdf import extract_text
from services.chunking import chunk_text
from services.retrieval import search_multiple
from services.reranking import rerank
from services.generation import answer_question
from services.rag import create_vector_store
from db import get_db, Document, QueryHistory, APIKey
from core.security import get_current_user, get_user_openai_key
import uuid
import json
import os
import time
from core.logger import get_logger

log = get_logger("upload")
router = APIRouter()

CHUNK_DIR = "storage/chunks"
INDEX_DIR = "storage/indexes"

os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "pptx", "ppt", "txt", "md"}


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '.{ext}'.")

    t0 = time.perf_counter()
    doc_id = str(uuid.uuid4())
    file_name = file.filename

    try:
        pages = extract_text(file.file, file.filename)
        if not pages:
            raise ValueError("No text could be extracted from the file.")
        chunks = chunk_text(pages, doc_id, file_name)
        if not chunks:
            raise ValueError("Document produced no chunks after splitting.")
        create_vector_store(chunks, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error("upload_failed", extra={"doc_id": doc_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to process document.")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.info("document_uploaded", extra={"doc_id": doc_id, "file_name": file_name, "latency_ms": latency_ms})

    with open(f"{CHUNK_DIR}/{doc_id}.json", "w") as f:
        json.dump(chunks, f)

    db.add(Document(
        doc_id=doc_id,
        user_id=current_user.id,
        file_name=file_name,
        uploaded_at=time.time(),
    ))
    await db.commit()

    return {"message": "Uploaded successfully", "doc_id": doc_id}


@router.get("/documents")
async def list_documents(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.user_id == current_user.id))
    docs = result.scalars().all()
    documents = []
    for doc in docs:
        if os.path.exists(f"{CHUNK_DIR}/{doc.doc_id}.json"):
            documents.append({
                "doc_id": doc.doc_id,
                "fileName": doc.file_name,
                "uploadedAt": doc.uploaded_at,
            })
    return {"documents": documents}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.doc_id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for path in [f"{CHUNK_DIR}/{doc_id}.json", f"{INDEX_DIR}/{doc_id}.index"]:
        if os.path.exists(path):
            os.remove(path)

    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully"}


@router.patch("/documents/{doc_id}/rename")
async def rename_document(
    doc_id: str,
    fileName: str = Form(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.doc_id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.file_name = fileName
    await db.commit()
    return {"message": "Renamed successfully", "fileName": fileName}


@router.post("/ask")
async def ask_question(
    doc_ids: str = Form(...),
    question: str = Form(...),
    history: str = Form(default="[]"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]

    # Verify all docs belong to this user
    for doc_id in id_list:
        result = await db.execute(
            select(Document).where(Document.doc_id == doc_id, Document.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail=f"Access denied to document {doc_id}")

    try:
        history_list = json.loads(history)
    except Exception:
        history_list = []

    # Get user's own OpenAI key
    openai_key = await get_user_openai_key(current_user.id, db)

    t0 = time.perf_counter()
    try:
        relevant_chunks = search_multiple(id_list, question)
        reranked_chunks = rerank(question, relevant_chunks)
        result = answer_question(question, reranked_chunks, history=history_list, openai_api_key=openai_key)
    except Exception as e:
        log.error("ask_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to answer question.")

    # Track usage
    key_result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    key_row = key_result.scalar_one_or_none()
    if key_row:
        key_row.total_calls += 1

    # Save to history
    db.add(QueryHistory(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        doc_ids=json.dumps(id_list),
        question=question,
        answer=result.get("answer", ""),
        created_at=time.time(),
    ))
    await db.commit()

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.info("ask_request", extra={"total_latency_ms": total_ms})
    return JSONResponse(content=result)