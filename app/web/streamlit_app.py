import os
import json
from pathlib import Path
from typing import List, Dict, Tuple

import streamlit as st
import chromadb

# ---------- Embeddings ----------
def embed_texts(texts: List[str]) -> List[List[float]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
            vectors: List[List[float]] = []
            # Gemini embed_content is typically per-content; loop is simplest and robust
            for t in texts:
                out = genai.embed_content(model=model_name, content=t)
                if isinstance(out, dict) and "embedding" in out:
                    vectors.append(out["embedding"])
                elif isinstance(out, dict) and "embeddings" in out and out["embeddings"]:
                    vectors.append(out["embeddings"][0]["values"])
                else:
                    raise RuntimeError("Unexpected embedding response")
            return vectors
        except Exception:
            pass

    # Fallback local embeddings
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs = model.encode(texts, show_progress_bar=False, convert_to_numpy=False)
    return [v.tolist() for v in vecs]

# ---------- Doc building ----------
def job_to_document(job: Dict) -> Dict:
    lines = []
    lines.append(f"Title: {job.get('postTitle','')}")
    lines.append(f"Organization: {job.get('organizationName','')}")
    if job.get("numVacancies") is not None:
        lines.append(f"Vacancies: {job['numVacancies']}")
    if job.get("salary"):
        lines.append(f"Salary: {job['salary']}")
    if job.get("experienceRequired"):
        lines.append(f"Experience: {job['experienceRequired']}")
    if job.get("qualification"):
        lines.append(f"Qualification: {job['qualification']}")
    if job.get("ageRequirement"):
        lines.append(f"Age: {job['ageRequirement']}")
    if job.get("location"):
        lines.append(f"Location: {job['location']}")
    if job.get("lastDate"):
        lines.append(f"Last Date: {job['lastDate']}")
    passage = "\n".join(lines)

    metadata = {
        "category": job.get("category"),
        "organizationName": job.get("organizationName"),
        "postTitle": job.get("postTitle"),
        "numVacancies": job.get("numVacancies"),
        "experienceRequired": job.get("experienceRequired"),
        "qualification": job.get("qualification"),
        "location": job.get("location"),
        "lastDate": job.get("lastDate"),
        "sourceUrl": job.get("sourceUrl"),
    }
    return {"id": job.get("sourceUrl"), "text": passage, "metadata": metadata}

def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

# ---------- Cached vector store ----------
@st.cache_resource(show_spinner=True)
def build_vector_store(jobs_jsonl_path: str, collection_name: str = "jobyaari_jobs"):
    jobs = read_jsonl(Path(jobs_jsonl_path))
    docs = [job_to_document(j) for j in jobs]

    client = chromadb.Client()  # in-memory for Streamlit Cloud
    coll = client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    ids = [d["id"] for d in docs]
    metas = [d["metadata"] for d in docs]
    texts = [d["text"] for d in docs]

    # Compute embeddings explicitly to avoid server-side embedding config
    vectors = embed_texts(texts)
    coll.add(ids=ids, metadatas=metas, embeddings=vectors, documents=texts)
    return client, coll

# ---------- LLM Answering ----------
SYSTEM_PROMPT = (
    "You are JobYaari Assistant. Use ONLY the provided context to answer.\n"
    "- If the user mentions a specific post title, answer ONLY for that post.\n"
    "- If the user asks for a field (Qualification, Experience, Vacancies, Salary, Last Date), "
    "return that field for the most relevant post and cite the source.\n"
    "- Otherwise, provide up to 5 concise bullet points with: Title, Organization, Vacancies, "
    "Experience, Qualification, Location, Last Date, Source.\n"
    "- If information is missing, reply 'Not specified'. Do not invent information."
)

def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    out = model.generate_content(prompt)
    return out.text if hasattr(out, "text") else str(out)

def make_context(docs: List[str], metas: List[Dict]) -> str:
    blocks = []
    for d, m in zip(docs, metas):
        blocks.append(f"{d}\nSource: {m.get('sourceUrl','')}")
    return "\n\n".join(blocks)

def retrieve(coll, query: str, top_k: int = 8) -> Dict:
    # Plain similarity search; let the LLM reason with context
    res = coll.query(query_texts=[query], n_results=top_k)
    return res

# ---------- UI ----------
st.set_page_config(page_title="JobYaari Chatbot", page_icon="💼", layout="centered")
st.title("JobYaari Chatbot")
st.caption("Ask about jobs by category, experience, qualification. Powered by Chroma + Gemini.")

# Build vector store once per session
data_path = "data/processed/jobs.jsonl"
client, coll = build_vector_store(data_path)

query = st.text_input("Your question", placeholder="What are the latest notifications in Engineering?")
if st.button("Ask") and query:
    with st.spinner("Thinking..."):
        res = retrieve(coll, query, top_k=8)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]

        context_text = make_context(docs, metas)
        prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context_text}\n\nUser Query: {query}\n\nAnswer:"
        answer = call_gemini(prompt)

        # Fallback: if LLM unavailable, show deterministic top matches
        if not answer.strip():
            lines = ["Top matches:"]
            for m in metas[:5]:
                lines.append(
                    f"- {m.get('postTitle','')} — {m.get('organizationName','')} | "
                    f"Vacancies: {m.get('numVacancies','N/A')} | Exp: {m.get('experienceRequired','N/A')} | "
                    f"Qual: {m.get('qualification','N/A')} | Last Date: {m.get('lastDate','N/A')} | "
                    f"Source: {m.get('sourceUrl','')}"
                )
            answer = "\n".join(lines)

    st.subheader("Answer")
    st.write(answer)