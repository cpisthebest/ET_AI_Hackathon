"""Ingest all PDFs from type-specific document folders.

Folder layout is the source of truth for document_type:

    data/documents/regulation/*.pdf -> REGULATION
    data/documents/control/*.pdf    -> CONTROL
    data/documents/evidence/*.pdf   -> EVIDENCE
    data/documents/policy/*.pdf     -> POLICY
    data/documents/assessment/*.pdf -> ASSESSMENT

No business/database records are hardcoded here.
"""
from pathlib import Path

from app.db.session import SessionLocal
from app.services.document_driven_ingestion import ingest_document_and_extract

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data" / "documents"

DOCUMENT_TYPES = {
    "regulation": "REGULATION",
    "control": "CONTROL",
    "evidence": "EVIDENCE",
    "policy": "POLICY",
    "assessment": "ASSESSMENT",
}


def discover_documents():
    """Yield (pdf_path, document_type) from the folder structure."""
    for folder_name, document_type in DOCUMENT_TYPES.items():
        folder = DOCS / folder_name
        if not folder.exists():
            continue

        for path in sorted(folder.glob("*.pdf")):
            yield path, document_type


def main():
    documents = list(discover_documents())
    if not documents:
        raise RuntimeError(f"No PDF documents found under {DOCS}")

    db = SessionLocal()
    try:
        for path, document_type in documents:
            print(f"Ingesting {path.relative_to(DOCS)} as {document_type}")
            result = ingest_document_and_extract(db, path, document_type)
            print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
