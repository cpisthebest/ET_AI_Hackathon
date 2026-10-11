from datetime import date
from sqlalchemy import select
from app.agents.graph import build_graph
from app.db.models import Obligation, Control, ObligationControlMapping, Gap, AuditEvent, RegulationVersion, Evidence, TestResult

def run_assessment(db, assessment_date: date):
    graph = build_graph(db)
    state = graph.invoke({"assessment_date": assessment_date.isoformat()})

    # Persist normalized traceability artifacts.
    versions = db.scalars(select(RegulationVersion)).all()
    version_id = versions[-1].id if versions else None

    for o in state.get("obligations", []):
        existing = db.scalar(select(Obligation).where(Obligation.obligation_key == o["obligation_key"]))
        if not existing and version_id:
            db.add(Obligation(
                regulation_version_id=version_id,
                obligation_key=o["obligation_key"], text=o["text"],
                subject=o["subject"], action=o["action"],
                frequency=o.get("frequency"), retention_years=o.get("retention_years"),
                applicability_rule=o.get("applicability_rule",""),
                effective_from=assessment_date
            ))
    db.flush()

    obligations = {o.obligation_key:o for o in db.scalars(select(Obligation)).all()}
    controls = {c.control_key:c for c in db.scalars(select(Control)).all()}
    for m in state.get("mappings", []):
        if m["control_key"] and m["obligation_key"] in obligations:
            exists = db.scalar(select(ObligationControlMapping).where(
                ObligationControlMapping.obligation_id == obligations[m["obligation_key"]].id,
                ObligationControlMapping.control_id == controls[m["control_key"]].id))
            if not exists:
                db.add(ObligationControlMapping(
                    obligation_id=obligations[m["obligation_key"]].id,
                    control_id=controls[m["control_key"]].id,
                    mapping_confidence=m["confidence"],
                    rationale="Agent-generated semantic mapping; requires human approval.",
                    approved=False
                ))

    # Persist every control/evidence test so the compliance lineage is queryable.
    controls_by_key = {c.control_key: c for c in db.scalars(select(Control)).all()}
    evidence_by_key = {e.evidence_key: e for e in db.scalars(select(Evidence)).all()}
    for t in state.get("tests", []):
        control = controls_by_key.get(t.get("control_key")) if t.get("control_key") else None
        evidence = evidence_by_key.get(t.get("evidence_key")) if t.get("evidence_key") else None
        if control:
            db.add(TestResult(
                control_id=control.id,
                evidence_id=evidence.id if evidence else None,
                test_name=f"Regulatory obligation test: {t['obligation_key']}",
                result=t["result"],
                score=t["score"],
                findings=t["findings"],
            ))

    persisted_gaps = []
    for g in state.get("gaps", []):
        gap = Gap(
            obligation_id=obligations[g["obligation_key"]].id,
            control_id=controls[g["control_key"]].id if g.get("control_key") else None,
            severity=g["severity"], title=g["title"],
            description=g["description"], evidence_basis=g["evidence_basis"],
            remediation=g["remediation"], human_approved=False
        )
        db.add(gap)
        persisted_gaps.append(gap)

    db.add(AuditEvent(
        event_type="ASSESSMENT_COMPLETED", entity_type="assessment",
        entity_id=str(assessment_date), actor="system",
        payload={"gap_count":len(persisted_gaps),"obligation_count":len(state.get("obligations",[]))}
    ))
    db.commit()

    return {
        "assessment_date": assessment_date.isoformat(),
        "obligations": state.get("obligations", []),
        "mappings": state.get("mappings", []),
        "tests": state.get("tests", []),
        "gaps": state.get("gaps", []),
        "remediation": state.get("remediation", [])
    }
