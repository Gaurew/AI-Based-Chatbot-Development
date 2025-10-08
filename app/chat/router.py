from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict
from .rag import RAGService


router = APIRouter(prefix="/api")
rag_service = RAGService()


class ChatRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, str]] = None


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat")
async def chat(req: ChatRequest):
    filters = req.filters or None
    if isinstance(filters, dict) and len(filters) == 0:
        filters = None
    retrieved = rag_service.retrieve(req.query, filters)
    result = rag_service.generate(req.query, retrieved)
    return result


