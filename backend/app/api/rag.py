from fastapi import APIRouter
from app.rag.ingestor import search_failure_patterns
from pydantic import BaseModel

router = APIRouter(prefix="/rag", tags=["rag"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


@router.post("/search")
async def search_patterns(payload: SearchRequest):
    results = await search_failure_patterns(payload.query, payload.top_k)
    return {"query": payload.query, "results": results}