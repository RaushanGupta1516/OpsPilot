from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
import google.generativeai as genai
import os
import uuid

# switched from sentence-transformers to gemini embeddings API
# reason: sentence-transformers pulls torch (532MB) which kills render free tier
_client = None

COLLECTION_NAME = "failure_patterns"
EMBEDDING_DIM = 768  # gemini text-embedding-004 output size


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(":memory:")
    return _client


def embed_text(text: str) -> List[float]:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


def ensure_collection():
    client = get_client()
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"[rag] created collection: {COLLECTION_NAME}")


def upsert_pattern(pattern: Dict[str, Any]):
    client = get_client()
    ensure_collection()

    text = f"{pattern['symptom']} {' '.join(pattern['error_signals'])}"
    vector = embed_text(text)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=pattern,
            )
        ],
    )


def search_patterns(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    client = get_client()
    ensure_collection()

    # use retrieval_query task type for search queries
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query",
    )
    vector = result["embedding"]

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
    )

    return [
        {
            "score": round(r.score, 3),
            "pattern": r.payload,
        }
        for r in results
    ]