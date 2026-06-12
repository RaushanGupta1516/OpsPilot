from app.rag.knowledge_base import FAILURE_PATTERNS
from app.rag.embeddings import upsert_pattern, ensure_collection

_ingested = False


async def ingest_knowledge_base():
    global _ingested

    # only ingest once per server startup
    if _ingested:
        return

    print(f"[rag] ingesting {len(FAILURE_PATTERNS)} failure patterns...")
    ensure_collection()

    for pattern in FAILURE_PATTERNS:
        upsert_pattern(pattern)

    _ingested = True
    print(f"[rag] ingestion complete")


async def search_failure_patterns(query: str, top_k: int = 3):
    from app.rag.embeddings import search_patterns
    return search_patterns(query, top_k)