from pathlib import Path
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from datetime import date
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Gap, AuditEvent
from app.services.document_driven_ingestion import ingest_document_and_extract
from app.services.assessment import run_assessment

app = FastAPI(title="Regulatory Compliance Agent", version="0.2.0")


def db_dep():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/documents/ingest")
async def ingest(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db=Depends(db_dep),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF is supported in this reference implementation.")

    document_type = document_type.upper()
    allowed = {"REGULATION", "CONTROL", "EVIDENCE", "POLICY", "ASSESSMENT"}
    if document_type not in allowed:
        raise HTTPException(400, f"document_type must be one of {sorted(allowed)}")

    target = Path("/app/data/documents") / Path(file.filename).name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(await file.read())

    try:
        return ingest_document_and_extract(db, target, document_type)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class AssessmentRequest(BaseModel):
    assessment_date: date


@app.post("/api/v1/assessments")
def assessment(req: AssessmentRequest, db=Depends(db_dep)):
    return run_assessment(db, req.assessment_date)


@app.get("/api/v1/gaps")
def gaps(db=Depends(db_dep)):
    rows = db.scalars(select(Gap).order_by(Gap.created_at.desc())).all()
    return [{
        "id": str(x.id),
        "severity": x.severity,
        "title": x.title,
        "description": x.description,
        "remediation": x.remediation,
        "status": x.status,
        "human_approved": x.human_approved,
    } for x in rows]


@app.post("/api/v1/gaps/{gap_id}/approve-remediation")
def approve(gap_id: str, db=Depends(db_dep)):
    gap = db.get(Gap, gap_id)
    if not gap:
        raise HTTPException(404, "Gap not found")
    gap.human_approved = True
    gap.status = "remediation_approved"
    db.add(AuditEvent(
        event_type="REMEDIATION_APPROVED",
        entity_type="gap",
        entity_id=gap_id,
        actor="human_reviewer",
        payload={},
    ))
    db.commit()
    return {"id": gap_id, "status": gap.status, "human_approved": True}
