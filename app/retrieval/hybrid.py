from sqlalchemy import select, func, desc
from app.db.models import DocumentChunk, SourceDocument
from app.retrieval.embeddings import embed
from app.config import settings


def hybrid_search(db, query: str, top_k: int | None = None, document_type: str | None = None):
    """Hybrid pgvector + PostgreSQL FTS retrieval with optional source-type filtering."""
    top_k = top_k or settings.top_k
    qvec = embed(query)
    distance = DocumentChunk.embedding.cosine_distance(qvec)
    vector_score = (1 - distance).label("vector_score")
    text_score = func.ts_rank_cd(
        func.to_tsvector("english", DocumentChunk.content),
        func.plainto_tsquery("english", query)
    ).label("text_score")
    score = (
        settings.hybrid_vector_weight * vector_score +
        settings.hybrid_text_weight * text_score
    ).label("hybrid_score")
    stmt = (
        select(DocumentChunk, vector_score, text_score, score)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
    )
    if document_type:
        stmt = stmt.where(SourceDocument.document_type == document_type.upper())
    return db.execute(stmt.order_by(desc(score)).limit(top_k)).all()
