from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
from google import genai
from google.genai import types
import os
import uuid

_client = None

COLLECTION_NAME = "failure_patterns"
EMBEDDING_DIM = 768  # gemini text-embedding-004 output size


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(":memory:")
    return _client


def get_genai_client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def embed_text(text: str) -> List[float]:
    client = get_genai_client()
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values


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

    genai_client = get_genai_client()
    result = genai_client.models.embed_content(
        model="text-embedding-004",
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    vector = result.embeddings[0].values

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