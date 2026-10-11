# Regulatory Compliance Agent — PostgreSQL + pgvector

Production-oriented reference implementation for continuously tracing:

**Regulations → obligations → applicability → controls → evidence → tests → gaps → remediation → monitoring**

> All included regulatory PDFs are synthetic demonstration data and are NOT real RBI or other regulatory publications.

## Architecture

- Python 3.12
- FastAPI REST API
- PostgreSQL 16 + pgvector
- SQLAlchemy 2.x
- Alembic migrations
- LangGraph orchestration
- Ollama for local LLM inference
- SentenceTransformers embeddings (default: `BAAI/bge-small-en-v1.5`)
- Hybrid retrieval: PostgreSQL full-text search + pgvector cosine similarity
- HNSW vector index
- Temporal regulation versioning (`effective_from`, `effective_to`, `supersedes_id`)
- SHA-256 document provenance
- Common `SourceDocument` layer with typed REGULATION / CONTROL / EVIDENCE / POLICY artifacts
- Explicit control/evidence document lineage while sharing one pgvector retrieval pipeline
- Audit events
- Human approval state for material remediation decisions
- Streamlit UI
- Pytest tests
- Docker Compose

## Demo scenario

`mock_regulation_2025.pdf` says:
1. Access reviews are annual.
2. Records are retained for 3 years.

`mock_regulation_2026.pdf` supersedes it and says:
1. Access reviews are quarterly.
2. Records are retained for 7 years.
3. Exceptions must be reported quarterly.

The bank control PDF initially describes annual access review and 3-year retention. Evidence demonstrates annual review. The agent therefore identifies:
- review frequency gap,
- retention gap,
- missing quarterly exception-reporting control.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000/docs
UI: http://localhost:8501

The first startup will create database tables and then download the embedding model. The demo ingestion script ingests regulation, control and evidence PDFs into one SourceDocument/chunk/vector layer and links them to their domain entities. Ollama models are pulled separately:

```bash
docker exec -it compliance_api alembic upgrade head
```

```bash
docker exec -it compliance_ollama ollama pull llama3.1:8b
```

Then ingest the synthetic documents:

```bash
docker exec -it compliance_api python -m scripts.ingest_demo
```

Or locally:

```bash
python -m scripts.ingest_demo
```

Run the assessment:

```bash
curl -X POST http://localhost:8000/api/v1/assessments/demo
```

## Production hardening

This repository is intentionally deployable but still a reference implementation. Before production:
- use managed PostgreSQL with backups/PITR,
- use object storage for immutable originals,
- move embedding/LLM calls behind resilient worker queues,
- add SSO/RBAC and tenant isolation,
- add secret management,
- configure TLS,
- add structured observability/tracing,
- add document malware scanning,
- add PII/DLP controls,
- establish model evaluation and prompt/version governance,
- require human approval for material regulatory interpretations and remediation closure.

## Core API

- `POST /api/v1/documents/ingest`
- `POST /api/v1/assessments`
- `GET /api/v1/assessments/{id}`
- `GET /api/v1/gaps`
- `POST /api/v1/gaps/{id}/approve-remediation`
- `GET /api/v1/audit-events`
- `GET /health`

## Document-driven control and evidence extraction

CONTROL and EVIDENCE PDFs are not seeded with hardcoded domain records. The ingestion flow stores the source document and pgvector chunks first, then uses the configured Ollama model to extract structured `Control` and `Evidence` records from the actual document text.

```text
PDF -> SourceDocument -> DocumentChunk + pgvector
                       -> Ollama extraction
                          -> Control / Evidence
                          -> ControlDocument / source_document_id
```

`POST /api/v1/documents/ingest` automatically performs this extraction for `CONTROL` and `EVIDENCE` document types. Evidence may initially remain unlinked when its control cannot be confidently resolved; the original source document is retained for later mapping.

Run the demo with:

```bash
alembic upgrade head
python -m scripts.ingest_demo
```

The demo script contains no `IAM-001` or `EVID-IAM-2026-Q4` domain-record seed. Those values are extracted from the PDFs.


## Document-driven ingestion

Business/domain records are not seeded in Python. `scripts/ingest_demo.py` only selects PDFs and document types. The pipeline performs:

`PDF -> SourceDocument -> page-aware chunks + pgvector -> Ollama structured extraction -> validated PostgreSQL entities -> provenance links`.

Supported extraction document types:
- `REGULATION`: regulatory document, versions, obligations
- `CONTROL`: internal controls + ControlDocument links
- `EVIDENCE`: evidence + explicit control links
- `ASSESSMENT`: mappings, test results, gaps, remediation artifacts when explicitly present in the PDF
- `POLICY`: policy facts are extracted and retained in the source/audit layer; add a Policy domain table when policy lifecycle management is required

No control ID, evidence ID, obligation key, owner, date, finding, or remediation action is hardcoded into the ingestion code.
