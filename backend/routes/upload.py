from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.pdf import extract_text
from services.chunking import chunk_text
from services.retrieval import search_multiple
from services.reranking import rerank
from services.generation import answer_question
from services.rag import create_vector_store, index_to_bytes, bytes_to_index
from db import get_db, Document, QueryHistory, APIKey, DocStore
from core.security import get_current_user, get_user_openai_key
from core.config import config
import uuid, json, os, time, base64
from core.logger import get_logger

log = get_logger("upload")
router = APIRouter()

CHUNK_DIR = config.chunk_dir
INDEX_DIR = config.index_dir
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "pptx", "ppt", "txt", "md"}


async def ensure_doc_on_disk(doc_id: str, db: AsyncSession) -> bool:
    """Restore chunks + index from DB if missing from disk (e.g. after redeploy)."""
    chunk_path = os.path.join(CHUNK_DIR, f"{doc_id}.json")
    index_path = os.path.join(INDEX_DIR, f"{doc_id}.index")
    if os.path.exists(chunk_path) and os.path.exists(index_path):
        return True
    result = await db.execute(select(DocStore).where(DocStore.doc_id == doc_id))
    store = result.scalar_one_or_none()
    if not store:
        return False
    with open(chunk_path, "w") as f:
        f.write(store.chunks_json)
    bytes_to_index(base64.b64decode(store.index_bytes), doc_id)
    return True


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '.{ext}'.")

    openai_key = await get_user_openai_key(current_user.id, db)

    t0 = time.perf_counter()
    doc_id = str(uuid.uuid4())
    file_name = file.filename

    try:
        from openai import OpenAI
        user_client = OpenAI(api_key=openai_key)

        pages = extract_text(file.file, file.filename)
        if not pages:
            raise ValueError("No text could be extracted from the file.")
        chunks = chunk_text(pages, doc_id, file_name)
        if not chunks:
            raise ValueError("Document produced no chunks after splitting.")

        # Pass user_client so embeddings use the user's own API key
        create_vector_store(chunks, doc_id, client=user_client)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error("upload_failed", extra={"doc_id": doc_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to process document.")

    chunk_path = os.path.join(CHUNK_DIR, f"{doc_id}.json")
    with open(chunk_path, "w") as f:
        json.dump(chunks, f)

    encoded_index = base64.b64encode(index_to_bytes(doc_id)).decode("utf-8")

    db.add(DocStore(
        doc_id=doc_id,
        chunks_json=json.dumps(chunks),
        index_bytes=encoded_index,
        created_at=time.time(),
    ))
    db.add(Document(
        doc_id=doc_id,
        user_id=current_user.id,
        workspace_id=None,
        file_name=file_name,
        uploaded_at=time.time(),
    ))
    await db.commit()

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.info("document_uploaded", extra={"doc_id": doc_id, "file_name": file_name, "latency_ms": latency_ms})
    return {"message": "Uploaded successfully", "doc_id": doc_id}


@router.get("/documents")
async def list_documents(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.user_id == current_user.id))
    docs = result.scalars().all()
    return {"documents": [
        {"doc_id": d.doc_id, "fileName": d.file_name, "uploadedAt": d.uploaded_at}
        for d in docs
    ]}


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

    store_result = await db.execute(select(DocStore).where(DocStore.doc_id == doc_id))
    store = store_result.scalar_one_or_none()
    if store:
        await db.delete(store)

    for path in [os.path.join(CHUNK_DIR, f"{doc_id}.json"),
                 os.path.join(INDEX_DIR, f"{doc_id}.index")]:
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

    for doc_id in id_list:
        result = await db.execute(
            select(Document).where(Document.doc_id == doc_id, Document.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail=f"Access denied to document {doc_id}")

    key_result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    key_row = key_result.scalar_one_or_none()
    if not key_row:
        raise HTTPException(status_code=400, detail="No OpenAI API key found.")
    if key_row.token_limit > 0 and key_row.tokens_used >= key_row.token_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Token limit reached ({key_row.token_limit:,}). Update your limit in Profile & Settings."
        )

    for doc_id in id_list:
        if not await ensure_doc_on_disk(doc_id, db):
            raise HTTPException(status_code=404, detail=f"Document data missing for {doc_id}.")

    try:
        history_list = json.loads(history)
    except Exception:
        history_list = []

    openai_key = await get_user_openai_key(current_user.id, db)

    t0 = time.perf_counter()
    try:
        from openai import OpenAI
        user_client = OpenAI(api_key=openai_key)
        relevant_chunks = search_multiple(id_list, question, client=user_client)
        reranked_chunks = rerank(question, relevant_chunks)
        result = answer_question(question, reranked_chunks, history=history_list, openai_api_key=openai_key)
    except Exception as e:
        log.error("ask_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to answer question.")
    
    tokens_this_call = result.get("usage", {}).get("total_tokens", 0)
    key_row.total_calls += 1
    key_row.tokens_used += tokens_this_call

    db.add(QueryHistory(
        id=str(uuid.uuid4()), user_id=current_user.id,
        doc_ids=json.dumps(id_list), question=question,
        answer=result.get("answer", ""), created_at=time.time(),
    ))
    await db.commit()

    log.info("ask_request", extra={"total_latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
    return JSONResponse(content=result)