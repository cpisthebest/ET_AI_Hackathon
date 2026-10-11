from langgraph.graph import StateGraph, END
from app.agents.state import ComplianceState
from app.agents.nodes import (
    regulatory_intelligence_node, obligation_extraction_node,
    mapping_node, effectiveness_node, gap_node, remediation_node
)

def build_graph(db):
    g = StateGraph(ComplianceState)
    g.add_node("regulatory_intelligence", lambda s: regulatory_intelligence_node(s, db))
    g.add_node("obligation_extraction", lambda s: obligation_extraction_node(s, db))
    g.add_node("control_mapping", lambda s: mapping_node(s, db))
    g.add_node("effectiveness_assessment", lambda s: effectiveness_node(s, db))
    g.add_node("gap_identification", lambda s: gap_node(s, db))
    g.add_node("remediation", lambda s: remediation_node(s, db))
    g.set_entry_point("regulatory_intelligence")
    g.add_edge("regulatory_intelligence", "obligation_extraction")
    g.add_edge("obligation_extraction", "control_mapping")
    g.add_edge("control_mapping", "effectiveness_assessment")
    g.add_edge("effectiveness_assessment", "gap_identification")
    g.add_edge("gap_identification", "remediation")
    g.add_edge("remediation", END)
    return g.compile()
