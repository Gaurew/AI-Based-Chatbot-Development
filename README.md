# AI-Based-Chatbot-Development
 It is a application that implements an AI-powered chatbot for the  JobYaari website (www.jobyaari.com) that can respond intelligently to user queries regarding  job notifications and categorized posts (Engineering, Science, Commerce, and  Education).
## JobYaari AI Chatbot — Streamlit Single-App (RAG on jobs.jsonl)

This repo contains a single Streamlit app that loads `data/processed/jobs.jsonl`, builds an in-memory Chroma index, and uses Gemini for retrieval-augmented answers. No separate API server is required.

### Prerequisites
- Python 3.10+
- A Google Gemini API key (free tier works for this demo)

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Set secrets (locally)
Windows PowerShell:
```powershell
setx GEMINI_API_KEY "your_api_key_here"
# optional
setx GEMINI_MODEL "gemini-1.5-flash"
```
macOS/Linux (bash):
```bash
export GEMINI_API_KEY="your_api_key_here"
export GEMINI_MODEL="gemini-1.5-flash" # optional
```

### 3) Run the app
```bash
streamlit run app/web/streamlit_app.py
```
What happens on first run:
- The app reads `data/processed/jobs.jsonl`
- Builds an in-memory Chroma collection and computes embeddings (Gemini or fallback to Sentence-Transformers)
- Caches the index; subsequent queries are fast

### 4) Ask questions in the UI
- Examples:
  - "What are the latest notifications in Engineering?"
  - "Show me a Science job which has 1 year of experience."
  - "Tell me Education qualification for Research Associate-II (RA-II) post."
- The app cites original sources (jobdetails URLs) for transparency.

### Deploy on Streamlit Cloud
1. Push this repo to GitHub
2. Streamlit Cloud → New app
   - Repo/branch: select this project
   - App file: `app/web/streamlit_app.py`
3. In Advanced settings → Secrets, add:
```
GEMINI_API_KEY = your_api_key_here
GEMINI_MODEL = gemini-1.5-flash
```
4. Deploy. The app will build the index from `data/processed/jobs.jsonl` at startup.

### Project layout
```
app/web/streamlit_app.py   # Streamlit app (RAG pipeline)
data/processed/jobs.jsonl  # Knowledge base used for retrieval
requirements.txt           # Python deps
.gitignore                 # Ignore env/.chroma etc.
```

### Notes
- No `.env`, `.chroma`, or `venv` in git. Streamlit Cloud secrets hold the API key.
- To refresh data, update `data/processed/jobs.jsonl` and redeploy.