from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import settings

@lru_cache
def model():
    return SentenceTransformer(settings.embedding_model)

def embed(text: str) -> list[float]:
    return model().encode(text, normalize_embeddings=True).tolist()
