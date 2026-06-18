from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
import os
import uuid
import httpx

_qdrant_client = None

COLLECTION_NAME = "failure_patterns"
EMBEDDING_DIM = 768


def get_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(":memory:")
    return _qdrant_client


def embed_text(text: str) -> List[float]:
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": EMBEDDING_DIM,
    }
    response = httpx.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["embedding"]["values"]


def embed_query(text: str) -> List[float]:
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": EMBEDDING_DIM,
    }
    response = httpx.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["embedding"]["values"]


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

    vector = embed_query(query)

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