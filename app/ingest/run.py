import argparse
import json
from pathlib import Path
from typing import List

from app.config import get_settings
from .chunk import job_to_document
from .vectorstore import get_client, upsert_documents


def read_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--collection", type=str, default="jobyaari_jobs")
    args = parser.parse_args()

    settings = get_settings()
    input_path = Path(args.input)
    jobs = read_jsonl(input_path)

    docs = [job_to_document(j) for j in jobs]
    client = get_client(settings.chroma_dir)
    coll = upsert_documents(client, args.collection, docs)
    print(f"[ingest] Upserted {len(docs)} documents into collection '{args.collection}'.")


if __name__ == "__main__":
    main()


