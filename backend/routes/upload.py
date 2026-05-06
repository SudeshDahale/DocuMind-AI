from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from services.pdf import extract_text
from services.chunking import chunk_text
from services.retrieval import search_multiple
from services.reranking import rerank
from services.generation import answer_question
from services.rag import create_vector_store
import uuid
import json
import os
import time

router = APIRouter()

CHUNK_DIR = "storage/chunks"
INDEX_DIR = "storage/indexes"
META_FILE = "storage/metadata.json"


# -------------------------
# HELPERS
# -------------------------
def load_metadata():
    if not os.path.exists(META_FILE):
        return {}
    with open(META_FILE, "r") as f:
        return json.load(f)


def save_metadata(meta):
    with open(META_FILE, "w") as f:
        json.dump(meta, f)


# -------------------------
# UPLOAD
# -------------------------
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "pptx", "ppt", "txt", "md"}

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    pages = extract_text(file.file, file.filename)
    doc_id = str(uuid.uuid4())
    file_name = file.filename

    chunks = chunk_text(pages, doc_id, file_name)
    create_vector_store(chunks, doc_id)

    with open(f"{CHUNK_DIR}/{doc_id}.json", "w") as f:
        json.dump(chunks, f)

    meta = load_metadata()
    meta[doc_id] = {"fileName": file_name, "uploadedAt": time.time()}
    save_metadata(meta)

    return {"message": "Uploaded successfully", "doc_id": doc_id}


# -------------------------
# LIST DOCUMENTS
# -------------------------
@router.get("/documents")
async def list_documents():
    meta = load_metadata()
    documents = []
    for doc_id, info in meta.items():
        if os.path.exists(f"{CHUNK_DIR}/{doc_id}.json"):
            documents.append({
                "doc_id": doc_id,
                "fileName": info.get("fileName", "Unknown"),
                "uploadedAt": info.get("uploadedAt", 0)
            })
    return {"documents": documents}


# -------------------------
# DELETE DOCUMENT
# -------------------------
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    chunk_path = f"{CHUNK_DIR}/{doc_id}.json"
    index_path = f"{INDEX_DIR}/{doc_id}.index"

    if not os.path.exists(chunk_path):
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(chunk_path):
        os.remove(chunk_path)
    if os.path.exists(index_path):
        os.remove(index_path)

    meta = load_metadata()
    meta.pop(doc_id, None)
    save_metadata(meta)

    return {"message": "Document deleted successfully"}


# -------------------------
# RENAME DOCUMENT
# -------------------------
@router.patch("/documents/{doc_id}/rename")
async def rename_document(doc_id: str, fileName: str = Form(...)):
    meta = load_metadata()
    if doc_id not in meta:
        raise HTTPException(status_code=404, detail="Document not found")
    meta[doc_id]["fileName"] = fileName
    save_metadata(meta)
    return {"message": "Renamed successfully", "fileName": fileName}


# -------------------------
# ASK QUESTION
# -------------------------
@router.post("/ask")
async def ask_question(
    doc_ids: str = Form(...),
    question: str = Form(...),
    history: str = Form(default="[]")
):
    id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]
    try:
        history_list = json.loads(history)
    except Exception:
        history_list = []

    relevant_chunks = search_multiple(id_list, question)
    reranked_chunks = rerank(question, relevant_chunks)
    result = answer_question(question, reranked_chunks, history=history_list)
    return JSONResponse(content=result)