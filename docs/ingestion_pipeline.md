# Ingestion pipeline

All PDF types follow the same technical pipeline:

```text
PDF
 ↓
SHA-256 provenance
 ↓
SourceDocument(document_type)
 ↓
page-aware chunking
 ↓
SentenceTransformer embedding
 ↓
DocumentChunk
 ↓
pgvector HNSW + PostgreSQL FTS
```

Domain linking is separate:

- `REGULATION` → `RegulatoryDocument` and `RegulationVersion`
- `CONTROL` → `ControlDocument` → `Control`
- `EVIDENCE` → `Evidence` → `Control`

This means one retrieval layer can search all artifacts while preserving business semantics and explicit compliance lineage.
