import os
import streamlit as st
import requests


API_URL = os.getenv("JOBYAARI_API_URL", "http://localhost:8000")

st.set_page_config(page_title="JobYaari Chatbot", page_icon="💼", layout="centered")
st.title("JobYaari Chatbot")
st.caption("Ask about jobs by category, experience, qualification. Powered by Chroma + Gemini.")

with st.sidebar:
    st.subheader("About")
    st.caption("This demo uses RAG over JobYaari data (Chroma + Gemini)")


query = st.text_input("Your question", placeholder="What are the latest notifications in Engineering?")
go = st.button("Ask")

if go and query:
    try:
        resp = requests.post(
            f"{API_URL}/api/chat",
            json={"query": query},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Request failed: {e}")
        st.stop()

    st.subheader("Answer")
    st.write(data.get("answer", ""))

    results = data.get("results", [])
    if results:
        st.subheader("Top Matches")
        for r in results:
            st.markdown(
                f"- **{r.get('postTitle','')}** — {r.get('organizationName','')}  "+
                f"Vacancies: {r.get('numVacancies','N/A')} | Exp: {r.get('experienceRequired','N/A')} | Qual: {r.get('qualification','N/A')}  "+
                f"Loc: {r.get('location','N/A')} | Last Date: {r.get('lastDate','N/A')}  "+
                f"[Source]({r.get('sourceUrl','')})"
            )


