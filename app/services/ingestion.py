"""Compatibility wrapper for the generic, business-record-free PDF ingestion."""
from app.services.document_ingestion import ingest_pdf, chunk_text
__all__ = ["ingest_pdf", "chunk_text"]
