"""Document -> LLM extraction -> validated PostgreSQL domain ingestion.

No business identifiers, names, dates, owners, frequencies, findings, or
remediation actions are embedded in this module. They must come from the
source document or from another already persisted entity referenced by it.
"""

import json
import re
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import llm
from app.db.models import (
    AuditEvent,
    Control,
    ControlDocument,
    Evidence,
    Gap,
    Obligation,
    ObligationControlMapping,
    RegulationVersion,
    RegulatoryDocument,
    Remediation,
    SourceDocument,
    TestResult,
)


PROMPTS: dict[str, str] = {
    "REGULATION": """
Extract regulatory metadata, versions, and obligations explicitly present in this document.
Do not infer or invent values. Return null when a field is absent.
For the regulator field:
- Extract the issuing authority from the document's title page,
  header, footer, or explicit issuing-authority section.
- Do not invent a regulator.
- If the document does not identify an issuing authority,
  return null.
Return JSON only:
{
  "regulation": {
    "title": "string",
    "regulator": "string or null",
    "publication_date": "YYYY-MM-DD or null"
  },
  "versions": [{
    "version_label": "string",
    "effective_from": "YYYY-MM-DD",
    "effective_to": "YYYY-MM-DD or null",
    "status": "string or null",
    "supersedes_version_label": "string or null"
  }],
  "obligations": [{
    "obligation_key": "string",
    "version_label": "string",
    "text": "string",
    "subject": "string",
    "action": "string",
    "frequency": "string or null",
    "retention_years": "integer or null",
    "applicability_rule": "string or null",
    "effective_from": "YYYY-MM-DD or null",
    "effective_to": "YYYY-MM-DD or null"
  }]
}
""",
    "CONTROL": """
Extract every internal control explicitly present in this document.
Do not invent identifiers or field values. Return null for missing optional fields.
Return JSON only:
{"controls":[{
  "control_key":"string",
  "name":"string",
  "description":"string",
  "owner":"string",
  "frequency":"string or null",
  "retention_years":"integer or null",
  "status":"string or null"
}]}
""",
    "EVIDENCE": """
Extract every evidence item explicitly present in this document.
The control_key must be explicitly stated in the source; do not infer it semantically.
Return JSON only:
{"evidence":[{
  "evidence_key":"string",
  "control_key":"string or null",
  "description":"string",
  "evidence_date":"YYYY-MM-DD or null",
  "metadata":{}
}]}
""",
    "ASSESSMENT": """
Extract assessment artifacts explicitly present in this document.
Do not invent relationships. A mapping/test/gap/remediation may reference entities by their explicit keys.
Return JSON only:
{
  "mappings":[{"obligation_key":"string","control_key":"string","confidence":"number","rationale":"string","approved":"boolean or null"}],
  "tests":[{"control_key":"string","evidence_key":"string or null","test_name":"string","result":"string","score":"number","findings":"string"}],
  "gaps":[{"obligation_key":"string","control_key":"string or null","severity":"string","title":"string","description":"string","evidence_basis":"string","remediation":"string","status":"string or null","human_approved":"boolean or null"}],
  "remediations":[{"gap_title":"string","action":"string","owner":"string or null","due_date":"YYYY-MM-DD or null","status":"string or null"}]
}
""",
    "POLICY": """
Extract internal policy statements that explicitly describe obligations, controls, ownership, procedures, or applicability.
This project currently has no separate Policy table, so return structured policy facts only.
Return JSON only:
{"policy_facts":[{"statement":"string","owner":"string or null","effective_from":"YYYY-MM-DD or null","effective_to":"YYYY-MM-DD or null"}]}
""",
}


# def _json_content(message: Any) -> Any:
#     content = getattr(message, "content", message)
#     if isinstance(content, list):
#         content = "".join(
#             part.get("text", "") if isinstance(part, dict) else str(part)
#             for part in content
#         )
#     text = str(content).strip()
#     text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
#     text = re.sub(r"\s*```$", "", text)
#     return json.loads(text)


def _json_content(message):
    content = getattr(message, "content", message)

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )

    text = str(content or "").strip()

    if not text:
        raise ValueError(
            "Ollama returned an empty response. "
            "Check the Ollama service, model, and container logs."
        )

    # Remove Markdown code fences.
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text)

    # First, try parsing the complete response.
    try:
        result = json.loads(text)
    except json.JSONDecodeError as original_error:
        # Recover a JSON object if the model added explanatory text.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise ValueError(
                f"Ollama did not return a JSON object. "
                f"Response begins with: {text[:500]!r}"
            ) from original_error

        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned invalid or incomplete JSON. "
                f"Response begins with: {text[:500]!r}"
            ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            f"Expected a JSON object, got {type(result).__name__}"
        )

    return result


def _source_text(db: Session, source_document_id) -> str:
    source = db.get(SourceDocument, source_document_id)
    if not source:
        raise ValueError(f"Source document {source_document_id} not found")
    chunks = sorted(source.chunks, key=lambda x: x.chunk_index)
    return "\n\n".join(
        f"[page={c.page_number or 'unknown'} chunk={c.id}]\n{c.content}"
        for c in chunks
    )


def extract(db: Session, source_document_id, document_type: str) -> dict:
    document_type = document_type.upper()
    if document_type not in PROMPTS:
        raise ValueError(f"Unsupported document type: {document_type}")

    prompt = (
        PROMPTS[document_type]
        + "\n\nSOURCE DOCUMENT:\n"
        + _source_text(db, source_document_id)
    )
    return _json_content(llm().invoke(prompt))


def _d(v):
    if v in (None, "", "null"):
        return None
    return date.fromisoformat(str(v))


def _bool(v, default=False):
    return default if v is None else bool(v)


def ingest_regulation(db: Session, source: SourceDocument, payload: dict) -> dict:
    metadata = payload.get("regulation") or {}
    title = str(metadata.get("title") or source.title).strip()
    regulator = metadata.get("regulator")
    if not regulator:
        raise ValueError("Regulation PDF did not contain a regulator")

    publication_date = _d(metadata.get("publication_date"))
    doc = db.scalar(select(RegulatoryDocument).where(
        RegulatoryDocument.source_document_id == source.id
    ))
    if doc is None:
        doc = RegulatoryDocument(
            source_document_id=source.id,
            title=title,
            regulator=str(regulator),
            publication_date=publication_date,
            sha256=source.sha256,
            source_uri=source.source_uri,
        )
        db.add(doc)
        db.flush()
    else:
        doc.title = title
        doc.regulator = str(regulator)
        doc.publication_date = publication_date

    versions = {}
    for item in payload.get("versions") or []:
        label = str(item.get("version_label") or "").strip()
        effective_from = _d(item.get("effective_from"))
        if not label or not effective_from:
            continue
        version = db.scalar(select(RegulationVersion).where(
            RegulationVersion.document_id == doc.id,
            RegulationVersion.version_label == label,
        ))
        if version is None:
            version = RegulationVersion(
                document_id=doc.id,
                version_label=label,
                effective_from=effective_from,
                effective_to=_d(item.get("effective_to")),
                status=str(item.get("status") or "active"),
            )
            db.add(version)
            db.flush()
        else:
            version.effective_from = effective_from
            version.effective_to = _d(item.get("effective_to"))
            version.status = str(item.get("status") or version.status)
        versions[label] = version

    db.flush()
    # Resolve cross-version supersession using labels extracted from documents.
    for item in payload.get("versions") or []:
        label = str(item.get("version_label") or "").strip()
        old_label = item.get("supersedes_version_label")
        if label in versions and old_label:
            old = db.scalar(select(RegulationVersion).where(
                RegulationVersion.version_label == str(old_label).strip()
            ))
            if old:
                versions[label].supersedes_id = old.id
                old.effective_to = versions[label].effective_from
                old.status = "superseded"

    obligations_created = 0
    for item in payload.get("obligations") or []:
        key = str(item.get("obligation_key") or "").strip()
        version_label = str(item.get("version_label") or "").strip()
        version = versions.get(version_label) or db.scalar(
            select(RegulationVersion).where(RegulationVersion.version_label == version_label)
        )
        if not key or version is None:
            continue

        obligation = db.scalar(select(Obligation).where(Obligation.obligation_key == key))
        values = dict(
            regulation_version_id=version.id,
            obligation_key=key,
            text=str(item.get("text") or "").strip(),
            subject=str(item.get("subject") or "").strip(),
            action=str(item.get("action") or "").strip(),
            frequency=item.get("frequency"),
            retention_years=item.get("retention_years"),
            applicability_rule=str(item.get("applicability_rule") or "").strip(),
            effective_from=_d(item.get("effective_from")) or version.effective_from,
            effective_to=_d(item.get("effective_to")),
            source_document_id=source.id,
        )
        if not values["text"] or not values["subject"] or not values["action"]:
            continue
        if obligation is None:
            db.add(Obligation(**values))
            obligations_created += 1
        else:
            for k, v in values.items():
                setattr(obligation, k, v)

    db.add(AuditEvent(
        event_type="DOCUMENT_INGESTED",
        entity_type="regulatory_document",
        entity_id=str(doc.id),
        actor="document_ingestion",
        payload={"source_document_id": str(source.id)},
    ))
    db.commit()
    return {"regulatory_document_id": str(doc.id), "versions": len(versions), "obligations": obligations_created}


def ingest_controls(db: Session, source: SourceDocument, payload: dict) -> dict:
    count = 0
    for item in payload.get("controls") or []:
        key = str(item.get("control_key") or "").strip()
        name = str(item.get("name") or "").strip()
        description = str(item.get("description") or "").strip()
        owner = str(item.get("owner") or "").strip()
        if not key or not name or not description or not owner:
            continue

        control = db.scalar(select(Control).where(Control.control_key == key))
        if control is None:
            control = Control(
                control_key=key,
                name=name,
                description=description,
                owner=owner,
                frequency=item.get("frequency"),
                retention_years=item.get("retention_years"),
                status=item.get("status") or "active",
            )
            db.add(control)
            db.flush()
            count += 1
        else:
            control.name = name
            control.description = description
            control.owner = owner
            control.frequency = item.get("frequency")
            control.retention_years = item.get("retention_years")
            if item.get("status"):
                control.status = item["status"]

        link = db.scalar(select(ControlDocument).where(
            ControlDocument.control_id == control.id,
            ControlDocument.source_document_id == source.id,
        ))
        if link is None:
            db.add(ControlDocument(control_id=control.id, source_document_id=source.id))

    db.add(AuditEvent(
        event_type="DOCUMENT_INGESTED",
        entity_type="control_document",
        entity_id=str(source.id),
        actor="document_ingestion",
        payload={"controls_created": count},
    ))
    db.commit()
    return {"controls_created": count}


def ingest_evidence(db: Session, source: SourceDocument, payload: dict) -> dict:
    count = 0
    unresolved = 0
    for item in payload.get("evidence") or []:
        key = str(item.get("evidence_key") or "").strip()
        if not key:
            continue
        control = None
        control_key = item.get("control_key")
        if control_key:
            control = db.scalar(select(Control).where(Control.control_key == str(control_key).strip()))
            if control is None:
                unresolved += 1

        evidence = db.scalar(select(Evidence).where(Evidence.evidence_key == key))
        values = dict(
            control_id=control.id if control else None,
            source_document_id=source.id,
            evidence_key=key,
            description=str(item.get("description") or "").strip(),
            evidence_date=_d(item.get("evidence_date")),
            source_uri=source.source_uri,
            sha256=source.sha256,
            metadata_json=item.get("metadata") or {},
        )
        if not values["description"]:
            continue
        if evidence is None:
            db.add(Evidence(**values))
            count += 1
        else:
            for k, v in values.items():
                setattr(evidence, k, v)

    db.add(AuditEvent(
        event_type="DOCUMENT_INGESTED",
        entity_type="evidence_document",
        entity_id=str(source.id),
        actor="document_ingestion",
        payload={"evidence_created": count, "unresolved_control_links": unresolved},
    ))
    db.commit()
    return {"evidence_created": count, "unresolved_control_links": unresolved}


def ingest_assessment(db: Session, source: SourceDocument, payload: dict) -> dict:
    """Load assessment artifacts only when their keys are explicitly present in the PDF."""
    mappings = tests = gaps = remediations = 0

    obligations = {x.obligation_key: x for x in db.scalars(select(Obligation)).all()}
    controls = {x.control_key: x for x in db.scalars(select(Control)).all()}
    evidence = {x.evidence_key: x for x in db.scalars(select(Evidence)).all()}

    for item in payload.get("mappings") or []:
        o = obligations.get(str(item.get("obligation_key") or "").strip())
        c = controls.get(str(item.get("control_key") or "").strip())
        if not o or not c:
            continue
        existing = db.scalar(select(ObligationControlMapping).where(
            ObligationControlMapping.obligation_id == o.id,
            ObligationControlMapping.control_id == c.id,
        ))
        if existing is None:
            db.add(ObligationControlMapping(
                obligation_id=o.id,
                control_id=c.id,
                mapping_confidence=float(item.get("confidence") or 0),
                rationale=str(item.get("rationale") or ""),
                approved=_bool(item.get("approved")),
                source_document_id=source.id,
            ))
            mappings += 1

    for item in payload.get("tests") or []:
        c = controls.get(str(item.get("control_key") or "").strip())
        if not c:
            continue
        e = evidence.get(str(item.get("evidence_key") or "").strip()) if item.get("evidence_key") else None
        db.add(TestResult(
            control_id=c.id,
            evidence_id=e.id if e else None,
            test_name=str(item.get("test_name") or "document test"),
            result=str(item.get("result") or "unknown"),
            score=float(item.get("score") or 0),
            findings=str(item.get("findings") or ""),
            source_document_id=source.id,
        ))
        tests += 1

    for item in payload.get("gaps") or []:
        o = obligations.get(str(item.get("obligation_key") or "").strip())
        c = controls.get(str(item.get("control_key") or "").strip()) if item.get("control_key") else None
        if not o:
            continue
        gap = Gap(
            obligation_id=o.id,
            control_id=c.id if c else None,
            severity=str(item.get("severity") or "unknown"),
            title=str(item.get("title") or ""),
            description=str(item.get("description") or ""),
            evidence_basis=str(item.get("evidence_basis") or ""),
            remediation=str(item.get("remediation") or ""),
            status=str(item.get("status") or "open"),
            human_approved=_bool(item.get("human_approved")),
            source_document_id=source.id,
        )
        if gap.title and gap.description:
            db.add(gap)
            gaps += 1

    db.flush()
    for item in payload.get("remediations") or []:
        title = str(item.get("gap_title") or "").strip()
        gap = None
        if title:
            gap = db.scalar(select(Gap).where(Gap.title == title).order_by(Gap.created_at.desc()))
        if not gap:
            continue
        action = str(item.get("action") or "").strip()
        if not action:
            continue
        db.add(Remediation(
            gap_id=gap.id,
            action=action,
            owner=item.get("owner"),
            due_date=_d(item.get("due_date")),
            status=item.get("status") or "proposed",
            source_document_id=source.id,
        ))
        remediations += 1

    db.add(AuditEvent(
        event_type="ASSESSMENT_DOCUMENT_INGESTED",
        entity_type="assessment_document",
        entity_id=str(source.id),
        actor="document_ingestion",
        payload={"mappings": mappings, "tests": tests, "gaps": gaps, "remediations": remediations},
    ))
    db.commit()
    return {"mappings": mappings, "tests": tests, "gaps": gaps, "remediations": remediations}


def ingest_document_and_extract(db: Session, path, document_type: str) -> dict:
    """Single entry point for PDF -> database ingestion."""
    from app.services.document_ingestion import ingest_pdf

    source = ingest_pdf(db, path, document_type)
    payload = extract(db, source.id, document_type)

    if document_type.upper() == "REGULATION":
        result = ingest_regulation(db, source, payload)
    elif document_type.upper() == "CONTROL":
        result = ingest_controls(db, source, payload)
    elif document_type.upper() == "EVIDENCE":
        result = ingest_evidence(db, source, payload)
    elif document_type.upper() == "ASSESSMENT":
        result = ingest_assessment(db, source, payload)
    elif document_type.upper() == "POLICY":
        result = {"policy_facts": len(payload.get("policy_facts") or [])}
        db.add(AuditEvent(
            event_type="POLICY_DOCUMENT_INGESTED",
            entity_type="policy_document",
            entity_id=str(source.id),
            actor="document_ingestion",
            payload=result,
        ))
        db.commit()
    else:
        raise ValueError(f"Unsupported document type: {document_type}")

    return {
        "source_document_id": str(source.id),
        "document_type": source.document_type,
        **result,
    }
