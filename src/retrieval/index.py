import argparse
import json
import re
from pathlib import Path

from src.io import digest, read_jsonl, write_json

EMBEDDING = "BAAI/bge-small-en-v1.5"
TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")


def tokenize(text):
    return TOKEN.findall(text.lower())


def build(chunks_path, out="index", dense=False, embedding=EMBEDDING):
    chunks = read_jsonl(chunks_path)
    if not chunks or len({c["chunk_id"] for c in chunks}) != len(chunks):
        raise ValueError("Index requires nonempty chunks with unique IDs")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if dense:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(embedding)
        vectors = model.encode([c["text"] for c in chunks], batch_size=32, normalize_embeddings=True)
        vectors = np.asarray(vectors, dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(out / "faiss.index"))
    write_json(out / "chunks.json", chunks)
    write_json(out / "metadata.json", {"schema": 1, "dense": dense,
                                       "embedding": embedding if dense else None,
                                       "corpus_hash": digest(chunks), "chunks": len(chunks)})
    return json.loads((out / "metadata.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--chunks", default="data/processed/chunks.jsonl")
    p.add_argument("--out", default="index")
    p.add_argument("--dense", action="store_true")
    a = p.parse_args()
    print(build(a.chunks, a.out, a.dense))
