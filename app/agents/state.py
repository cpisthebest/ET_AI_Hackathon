from typing import TypedDict, Any

class ComplianceState(TypedDict, total=False):
    assessment_date: str
    regulatory_chunks: list[dict[str, Any]]
    obligations: list[dict[str, Any]]
    controls: list[dict[str, Any]]
    mappings: list[dict[str, Any]]
    tests: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    remediation: list[dict[str, Any]]
    mapping_sources: dict[str, Any]
    evidence_sources: dict[str, Any]
    audit: list[dict[str, Any]]
