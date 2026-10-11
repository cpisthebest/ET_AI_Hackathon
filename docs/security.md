# Security / production checklist

- SSO/OIDC with RBAC.
- Tenant isolation with PostgreSQL RLS.
- Encrypt PostgreSQL and object storage at rest.
- TLS in transit.
- Secrets from Vault/KMS/secret manager.
- Immutable source-document storage.
- SHA-256 plus signed metadata for provenance.
- Virus/malware scanning before parsing.
- Prompt injection defenses for untrusted documents.
- Treat retrieved document text as data, never instructions.
- Schema-constrained LLM output and deterministic validators.
- Human approval before material regulatory interpretation, remediation acceptance, or control closure.
- Full audit trail for ingestion, extraction, mappings, tests, approvals and changes.
- Model/prompt/version registry.
- PII classification and redaction.
