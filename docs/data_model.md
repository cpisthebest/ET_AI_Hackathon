# Traceability data model

The implementation separates the common searchable document layer from compliance-domain entities.

```text
SourceDocument
  ├── REGULATION → RegulatoryDocument → RegulationVersion → Obligation
  ├── CONTROL    → ControlDocument ───────────────────────→ Control
  ├── EVIDENCE   ─────────────────────────────────────────→ Evidence
  └── POLICY

SourceDocument → DocumentChunk → pgvector + PostgreSQL FTS

Obligation → ObligationControlMapping → Control → Evidence → TestResult → Gap → Remediation
```

## Why this model

- A PDF is a source artifact; its business meaning is represented by a domain entity.
- All source types share one ingestion, provenance, chunking and pgvector pipeline.
- Controls and evidence are no longer represented as fake regulatory documents.
- Retrieval can be restricted by `document_type` so regulatory intelligence searches regulations, control mapping searches controls, and effectiveness testing searches evidence.
- Explicit foreign keys provide auditable lineage; embeddings are used for candidate discovery rather than as the system of record.

## Point-in-time regulation

Regulation versions retain `effective_from`, `effective_to`, `supersedes_id` and `status`. This supports historical assessments without conflating current and historical requirements.

For a production multi-bank deployment, add `tenant_id` to every business table and enforce PostgreSQL Row Level Security.
