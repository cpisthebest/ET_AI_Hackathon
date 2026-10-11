"""Backward-compatible entry points for document-driven domain ingestion."""

from app.services.document_driven_ingestion import (
    extract,
    ingest_controls,
    ingest_evidence,
    ingest_regulation,
    ingest_assessment,
)


def extract_controls(db, source_document_id):
    from app.db.models import SourceDocument
    source = db.get(SourceDocument, source_document_id)
    payload = extract(db, source_document_id, "CONTROL")
    return ingest_controls(db, source, payload)


def extract_evidence(db, source_document_id):
    from app.db.models import SourceDocument
    source = db.get(SourceDocument, source_document_id)
    payload = extract(db, source_document_id, "EVIDENCE")
    return ingest_evidence(db, source, payload)
