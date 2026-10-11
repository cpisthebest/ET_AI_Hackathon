# Agent design

## 1. Regulatory Intelligence Agent
Finds relevant regulatory passages using hybrid lexical/vector retrieval and records provenance.

## 2. Change Intelligence Agent
Compares temporally effective regulation versions. A production implementation should perform clause-level diffs and classify changes as:
- unchanged,
- modified,
- added,
- removed,
- superseded.

## 3. Obligation Extraction Agent
Converts clauses into structured obligations:
subject, action, frequency, retention, applicability and effective dates.

## 4. Control Mapping Agent
Maps obligations to controls using semantic retrieval plus deterministic business rules. Mapping is marked as requiring human approval.

## 5. Effectiveness Agent
Tests control design against obligations and available evidence. It distinguishes:
- design gap,
- operating effectiveness failure,
- evidence deficiency,
- no-control condition.

## 6. Gap & Remediation Agent
Creates severity-ranked gaps and proposed remedies. Material remediation requires human approval.

## 7. Monitoring Agent
In production, schedule recurring checks:
- new regulatory documents,
- changes to effective versions,
- expiring evidence,
- control frequency breaches,
- overdue remediation,
- stale mappings.

LangGraph is used for explicit orchestration rather than an unconstrained autonomous loop.
