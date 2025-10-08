from typing import List
import os


def embed_texts(texts: List[str]) -> List[List[float]]:
    # Simple pluggable embedding function.
    # Default: use Gemini embeddings if key present; else fall back to sentence-transformers (all-MiniLM-L6-v2).
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
            out = genai.embed_content(model=model, content=texts)
            if isinstance(out, dict) and "embedding" in out:
                return [out["embedding"]]
            if isinstance(out, dict) and "embeddings" in out:
                return [e["values"] for e in out["embeddings"]]
        except Exception:
            pass

    # Fallback local embeddings
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=False)
    return [v.tolist() for v in vectors]


