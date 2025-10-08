from typing import List, Dict
import chromadb


def get_client(persist_dir: str | None = None):
    if persist_dir:
        return chromadb.PersistentClient(path=persist_dir)
    return chromadb.Client()


def upsert_documents(client, collection_name: str, docs: List[Dict]):
    coll = client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    ids = [d["id"] for d in docs]
    metadatas = [d["metadata"] for d in docs]
    documents = [d["text"] for d in docs]

    coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return coll


