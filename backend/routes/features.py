from fastapi import APIRouter, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from openai import OpenAI
from core.config import config
from core.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db, DocStore
from core.security import get_current_user, get_user_openai_key
import json
import os
import base64

router = APIRouter()
log = get_logger("features")

CHUNK_DIR = "storage/chunks"
INDEX_DIR = "storage/indexes"


async def _load_chunks_with_restore(doc_id: str, db: AsyncSession) -> list:
    """Load chunks from disk, restoring from DB if missing after redeploy."""
    path = os.path.join(CHUNK_DIR, f"{doc_id}.json")
    if not os.path.exists(path):
        result = await db.execute(select(DocStore).where(DocStore.doc_id == doc_id))
        store = result.scalar_one_or_none()
        if not store:
            return []
        os.makedirs(CHUNK_DIR, exist_ok=True)
        with open(path, "w") as f:
            f.write(store.chunks_json)
    with open(path, "r") as f:
        return json.load(f)


@router.post("/explain")
async def explain_document(
    doc_ids: str = Form(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    all_chunks = []
    for doc_id in id_list:
        chunks = await _load_chunks_with_restore(doc_id, db)
        all_chunks.extend(chunks[:60 // len(id_list)])

    if not all_chunks:
        raise HTTPException(status_code=404, detail="No content found for the given documents")

    combined_text = ""
    for chunk in all_chunks[:40]:
        combined_text += chunk.get("text", "") + "\n\n"
        if len(combined_text) > 6000:
            break

    openai_key = await get_user_openai_key(current_user.id, db)
    client = OpenAI(api_key=openai_key)

    prompt = f"""You are an expert document tutor. Analyze the document content below and produce a structured section-by-section explanation.

For each major section or topic you identify, provide:
1. A clear section title
2. A 2-3 sentence plain-English explanation of what it covers
3. 2-3 key takeaways as bullet points
4. The difficulty level: Beginner / Intermediate / Advanced

Return ONLY valid JSON in this exact format:
{{
  "document_summary": "One paragraph overview of the entire document",
  "total_sections": <number>,
  "sections": [
    {{
      "title": "Section title",
      "explanation": "Plain-English explanation",
      "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
      "difficulty": "Beginner|Intermediate|Advanced",
      "page_hint": "e.g. Pages 1-3 or Introduction"
    }}
  ]
}}

Document content:
{combined_text[:5000]}"""

    try:
        response = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise document analysis assistant. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return JSONResponse(content=result)
    except Exception as e:
        log.error("explain_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to explain document")


@router.post("/compare")
async def compare_documents(
    doc_id_a: str = Form(...),
    doc_id_b: str = Form(...),
    focus: str = Form(default=""),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunks_a = await _load_chunks_with_restore(doc_id_a, db)
    chunks_b = await _load_chunks_with_restore(doc_id_b, db)

    if not chunks_a or not chunks_b:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    name_a = chunks_a[0].get("fileName", "Document A") if chunks_a else "Document A"
    name_b = chunks_b[0].get("fileName", "Document B") if chunks_b else "Document B"

    text_a = "\n\n".join(c.get("text", "") for c in chunks_a[:25])[:3500]
    text_b = "\n\n".join(c.get("text", "") for c in chunks_b[:25])[:3500]
    focus_line = f"\nFocus the comparison specifically on: {focus}" if focus.strip() else ""

    prompt = f"""You are an expert analyst. Compare these two documents thoroughly.{focus_line}

Document A — "{name_a}":
{text_a}

---

Document B — "{name_b}":
{text_b}

Return ONLY valid JSON in this exact format:
{{
  "doc_a_name": "{name_a}",
  "doc_b_name": "{name_b}",
  "overview": "2-3 sentence high-level comparison",
  "similarities": [
    {{"point": "similarity description", "detail": "supporting detail"}}
  ],
  "differences": [
    {{"aspect": "aspect being compared", "doc_a": "how doc A handles it", "doc_b": "how doc B handles it", "winner": "A|B|Tie"}}
  ],
  "unique_to_a": ["topic or section only in Document A"],
  "unique_to_b": ["topic or section only in Document B"],
  "recommendation": "Which document is better suited for what purpose and why",
  "similarity_score": <0-100 integer representing overall similarity>
}}"""

    openai_key = await get_user_openai_key(current_user.id, db)
    client = OpenAI(api_key=openai_key)

    try:
        response = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise comparison analyst. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return JSONResponse(content=result)
    except Exception as e:
        log.error("compare_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to compare documents")


@router.post("/report")
async def generate_report(
    doc_ids: str = Form(...),
    report_type: str = Form(default="executive"),
    custom_instructions: str = Form(default=""),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    all_chunks = []
    for doc_id in id_list:
        chunks = await _load_chunks_with_restore(doc_id, db)
        all_chunks.extend(chunks[:30])

    if not all_chunks:
        raise HTTPException(status_code=404, detail="No content found")

    combined_text = "\n\n".join(c.get("text", "") for c in all_chunks[:50])[:6000]

    type_instructions = {
        "executive": "Create a concise executive summary for senior stakeholders. Focus on key findings, business implications, and recommended actions. Use business language.",
        "technical": "Create a detailed technical report. Include methodology, data points, technical specifications, and implementation details. Use precise technical language.",
        "summary": "Create a comprehensive structured summary suitable for all audiences. Cover all major points clearly and concisely.",
    }

    instruction = type_instructions.get(report_type, type_instructions["summary"])
    extra = f"\nAdditional instructions: {custom_instructions}" if custom_instructions.strip() else ""

    prompt = f"""{instruction}{extra}

Based on the following document content, generate a professional report in JSON format.

Return ONLY valid JSON:
{{
  "title": "Generated report title",
  "report_type": "{report_type}",
  "executive_summary": "2-3 paragraph overview",
  "sections": [
    {{
      "heading": "Section heading",
      "content": "Section body text — 2-4 paragraphs",
      "highlights": ["key point 1", "key point 2"]
    }}
  ],
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "conclusion": "Concluding paragraph",
  "metadata": {{
    "word_count_estimate": <number>,
    "reading_time_minutes": <number>,
    "confidence_score": <0-100>
  }}
}}

Document content:
{combined_text}"""

    openai_key = await get_user_openai_key(current_user.id, db)
    client = OpenAI(api_key=openai_key)

    try:
        response = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional report writer. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return JSONResponse(content=result)
    except Exception as e:
        log.error("report_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to generate report")