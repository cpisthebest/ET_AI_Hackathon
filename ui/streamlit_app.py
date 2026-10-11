import os, requests, streamlit as st
API = os.getenv("API_URL","http://api:8000")
st.set_page_config(page_title="Compliance Agent", layout="wide")
st.title("Regulatory Compliance Agent")
st.caption("Synthetic demo — PostgreSQL + pgvector + LangGraph + Ollama")

if st.button("Run 2026 compliance assessment"):
    r = requests.post(f"{API}/api/v1/assessments/demo", timeout=180)
    if r.ok:
        data = r.json()
        st.metric("Gaps", len(data["gaps"]))
        st.subheader("Traceability")
        st.json(data)
    else:
        st.error(r.text)

if st.button("Refresh gaps"):
    r = requests.get(f"{API}/api/v1/gaps")
    st.dataframe(r.json(), use_container_width=True)
