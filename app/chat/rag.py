from typing import List, Dict, Optional, Tuple
import os
import chromadb
from app.chat.prompts import SYSTEM_PROMPT


class RAGService:
    def __init__(self, collection_name: str = "jobyaari_jobs") -> None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", ".chroma")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_collection(collection_name)

    def _extract_filters_from_query(self, query: str) -> Tuple[Optional[Dict], List[Dict]]:
        # returns (where_filter_for_chroma, post_filters)
        q = query.lower()
        clauses: List[Dict] = []
        post: List[Dict] = []

        # category keywords
        for cat in ["engineering", "science", "commerce", "education"]:
            if cat in q:
                clauses.append({"category": cat})
                break

        # vacancies numeric constraints
        import re
        m = re.search(r"(vacanc(?:y|ies)|opening\w*)[^\d]*([<>]=?|at least|more than|greater than|over|less than|under|below)?\s*(\d+)", q)
        if m:
            op_word = (m.group(2) or "").strip()
            value = int(m.group(3))
            cmp_map = {
                ">": "$gt",
                ">=": "$gte",
                "<": "$lt",
                "<=": "$lte",
            }
            chroma_op = None
            if op_word in (">", ">=", "<", "<="):
                chroma_op = cmp_map[op_word]
            elif op_word in ("more than", "greater than", "over"):
                chroma_op = "$gt"
            elif op_word in ("at least",):
                chroma_op = "$gte"
            elif op_word in ("less than", "under", "below"):
                chroma_op = "$lt"
            else:
                # default to >= when just a number is present
                chroma_op = "$gte"

            clauses.append({"numVacancies": {chroma_op: value}})
            post.append({"numVacancies": {chroma_op: value}})

        where = None
        if len(clauses) == 1:
            where = clauses[0]
        elif len(clauses) > 1:
            where = {"$and": clauses}

        return where, post

    def _apply_post_filters(self, metas: List[Dict], post_filters: List[Dict]) -> List[Dict]:
        if not post_filters:
            return metas
        def match(meta: Dict) -> bool:
            for f in post_filters:
                for k, v in f.items():
                    if isinstance(v, dict):
                        # numeric comparison
                        for op, num in v.items():
                            val = meta.get(k)
                            if val is None:
                                return False
                            try:
                                x = int(val)
                            except Exception:
                                return False
                            if op == "$gt" and not (x > num):
                                return False
                            if op == "$gte" and not (x >= num):
                                return False
                            if op == "$lt" and not (x < num):
                                return False
                            if op == "$lte" and not (x <= num):
                                return False
                    else:
                        if str(meta.get(k, "")).lower() != str(v).lower():
                            return False
            return True
        return [m for m in metas if match(m)]

    def retrieve(self, query: str, filters: Optional[Dict] = None, top_k: int = 8) -> Dict:
        # Build filters from query if UI did not pass structured filters
        where, post_filters = self._extract_filters_from_query(query)
        # If caller provided filters, merge
        if filters:
            clauses = []
            if where is None and filters:
                # simple exact merge
                where = {}
            if where and "$and" in where:
                clauses.extend(where["$and"])
            elif where:
                clauses.append(where)
            for key in ["category", "experienceRequired", "qualification"]:
                val = filters.get(key) if isinstance(filters, dict) else None
                if val:
                    clauses.append({key: val})
            if len(clauses) == 1:
                where = clauses[0]
            elif len(clauses) > 1:
                where = {"$and": clauses}

        if where:
            res = self.collection.query(query_texts=[query], n_results=top_k, where=where)
        else:
            res = self.collection.query(query_texts=[query], n_results=top_k)

        # Apply post-filters to ensure constraints like vacancies > N are respected
        metas = res.get("metadatas", [[]])[0]
        docs = res.get("documents", [[]])[0]
        filtered_metas = self._apply_post_filters(metas, post_filters)
        # keep alignment with docs (filter by index)
        if len(filtered_metas) != len(metas):
            kept = []
            kept_docs = []
            for meta, doc in zip(metas, docs):
                if meta in filtered_metas:
                    kept.append(meta)
                    kept_docs.append(doc)
            res["metadatas"] = [kept]
            res["documents"] = [kept_docs]
        return res

    def generate(self, query: str, retrieved: Dict) -> Dict:
        # Build context
        docs = retrieved.get("documents", [[]])[0]
        metas = retrieved.get("metadatas", [[]])[0]
        context_blocks = []
        for doc, meta in zip(docs, metas):
            block = f"Context:\n{doc}\nSource: {meta.get('sourceUrl','')}"
            context_blocks.append(block)
        context_text = "\n\n".join(context_blocks)

        # Utilities to improve exact-post targeting
        def extract_title_from_query(q: str) -> Optional[str]:
            import re
            ql = q.lower()
            # heuristic: capture text after 'for ' and before ' post'
            m = re.search(r"for\s+(.+?)\s+post", ql)
            if m:
                return m.group(1).strip()
            # capture quoted text
            m = re.search(r"'([^']+)'|\"([^\"]+)\"", q)
            if m:
                return (m.group(1) or m.group(2)).strip()
            # fallback: look for parentheses content
            m = re.search(r"([a-z0-9\-\s]+\([^\)]+\))", ql)
            if m:
                return m.group(1).strip()
            return None

        def retrieve_by_title(title: str):
            # Title-only retrieval to bias vector search towards the exact post
            try:
                return self.collection.query(query_texts=[title], n_results=25)
            except Exception:
                return None

        # If the user asked for a specific field for a given post, prefer exact title match across the whole collection
        ql = query.lower()
        def select_best_by_title(q: str, candidates: List[Dict]) -> Optional[Dict]:
            if not candidates:
                return None
            words = set([w for w in q.lower().split() if len(w) > 2])
            best = None
            best_score = -1
            for m in candidates:
                title = (m.get("postTitle") or "").lower()
                # score: token overlap + substring bonus
                overlap = sum(1 for w in words if w in title)
                substr_bonus = 5 if any(''.join(w.split()) in ''.join(title.split()) for w in words) else 0
                score = overlap + substr_bonus
                if score > best_score:
                    best_score = score
                    best = m
            return best

        field_direct = None
        field_name = None
        target_meta = None
        if "qualification" in ql:
            field_name = "qualification"
        elif "experience" in ql:
            field_name = "experienceRequired"
        elif "vacanc" in ql or "opening" in ql:
            field_name = "numVacancies"
        elif "salary" in ql:
            field_name = "salary"
        elif "last date" in ql or "deadline" in ql:
            field_name = "lastDate"

        if field_name:
            title_hint = extract_title_from_query(query)
            search_metas = metas
            # If a title is hinted, do a dedicated retrieval using only the title
            if title_hint:
                rer = retrieve_by_title(title_hint)
                if rer:
                    search_metas = rer.get("metadatas", [[]])[0] or metas
            # Select best match from the search set
            target_meta = select_best_by_title(query, search_metas)
            if target_meta and target_meta.get(field_name) is not None:
                val = target_meta.get(field_name)
                title = target_meta.get("postTitle", "")
                org = target_meta.get("organizationName", "")
                src = target_meta.get("sourceUrl", "")
                field_label = field_name.replace("Required", "").title()
                field_direct = f"{field_label} for '{title}' ({org}): {val}\nSource: {src}"

        if field_direct:
            results = []
            sources = [target_meta.get("sourceUrl")] if target_meta else []
            return {"answer": field_direct, "results": results, "sources": sources}

        # Generate with Gemini, but fail gracefully with a deterministic fallback
        def fallback_answer() -> str:
            if not metas:
                return "No matching jobs found. Try different filters or query."
            lines = ["Top matches:"]
            for m in metas[:5]:
                lines.append(
                    f"- {m.get('postTitle','')} — {m.get('organizationName','')} | Vacancies: {m.get('numVacancies','N/A')} | Exp: {m.get('experienceRequired','N/A')} | Qual: {m.get('qualification','N/A')} | Last Date: {m.get('lastDate','N/A')} | Source: {m.get('sourceUrl','')}"
                )
            return "\n".join(lines)

        answer = None
        used_fallback = False
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("Missing GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            model = genai.GenerativeModel(model_name)
            prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context_text}\n\nUser Query: {query}\n\nAnswer:"
            out = model.generate_content(prompt)
            answer = out.text if hasattr(out, "text") else str(out)
        except Exception:
            answer = fallback_answer()
            used_fallback = True

        # Prepare compact results list
        results = []
        for meta in metas:
            results.append({
                "organizationName": meta.get("organizationName"),
                "category": meta.get("category"),
                "numVacancies": meta.get("numVacancies"),
                "experienceRequired": meta.get("experienceRequired"),
                "qualification": meta.get("qualification"),
                "sourceUrl": meta.get("sourceUrl"),
                "postTitle": meta.get("postTitle"),
                "location": meta.get("location"),
                "lastDate": meta.get("lastDate"),
            })

        sources = [m.get("sourceUrl") for m in metas]
        if used_fallback:
            # Avoid duplicate rendering in UI by returning the list only in the answer
            results = []
        return {"answer": answer, "results": results, "sources": sources}


