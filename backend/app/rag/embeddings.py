from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import uuid

# using in-memory qdrant for dev - no external service needed
# TODO: switch to qdrant cloud for production
_client = None
_model = None

COLLECTION_NAME = "failure_patterns"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output size


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(":memory:")
    return _client


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("[rag] loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[rag] model loaded")
    return _model


def embed_text(text: str) -> List[float]:
    model = get_model()
    return model.encode(text).tolist()


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

    # combine symptom + error signals for richer embedding
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

    vector = embed_text(query)
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