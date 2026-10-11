"""Generic PDF ingestion. This layer stores only facts about the source document itself."""

from pathlib import Path
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import DocumentChunk, SourceDocument
from app.retrieval.embeddings import embed
from app.services.provenance import sha256_file


def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    step = max(1, settings.chunk_size - settings.chunk_overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + settings.chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def ingest_pdf(db: Session, path: str | Path, document_type: str) -> SourceDocument:
    """Ingest a PDF without creating any business/domain records.

    The only caller-supplied domain metadata is document_type, which describes
    how the uploaded file should be interpreted. All business values are
    extracted from the PDF later.
    """
    path = Path(path)
    sha = sha256_file(path)

    source = db.scalar(select(SourceDocument).where(SourceDocument.sha256 == sha))
    if source:
        return source

    source = SourceDocument(
        document_type=document_type.upper(),
        title=path.stem,
        sha256=sha,
        source_uri=str(path),
    )
    db.add(source)
    db.flush()

    reader = PdfReader(str(path))
    chunk_index = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        for chunk in chunk_text(text):
            db.add(DocumentChunk(
                document_id=source.id,
                chunk_index=chunk_index,
                page_number=page_number,
                content=chunk,
                embedding=embed(chunk),
            ))
            chunk_index += 1

    db.commit()
    db.refresh(source)
    return source
