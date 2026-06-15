from app.rag.knowledge_base import FAILURE_PATTERNS
from app.rag.embeddings import upsert_pattern, ensure_collection

_ingested = False


async def ingest_knowledge_base():
    global _ingested

    if _ingested:
        return

    print(f"[rag] ingesting {len(FAILURE_PATTERNS)} failure patterns...")

    try:
        ensure_collection()
        for pattern in FAILURE_PATTERNS:
            upsert_pattern(pattern)
        _ingested = True
        print(f"[rag] ingestion complete")
    except Exception as e:
        print(f"[rag] ingestion failed (non-fatal): {e}")
        print(f"[rag] server will start without RAG — agent will use LLM fallback only")


async def search_failure_patterns(query: str, top_k: int = 3):
    from app.rag.embeddings import search_patterns
    try:
        return search_patterns(query, top_k)
    except Exception as e:
        print(f"[rag] search failed: {e}")
        return []