import json
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from src.io import digest
from src.retrieval.index import tokenize


def available_as_of(chunk):
    dates = [chunk["date_issued"], chunk.get("version_date") or chunk["date_issued"]]
    # Unreviewed web snapshots may contain amendments newer than their cover date.
    if chunk.get("metadata_status") == "draft" and chunk.get("retrieved_at"):
        dates.append(chunk["retrieved_at"][:10])
    return max(dates)


class Searcher:
    def __init__(self, folder="index", rerank=False, chunks=None):
        self.folder = Path(folder)
        self.meta = {} if chunks is not None else json.loads((self.folder / "metadata.json").read_text(encoding="utf-8"))
        self.chunks = chunks if chunks is not None else json.loads((self.folder / "chunks.json").read_text(encoding="utf-8"))
        if not self.chunks:
            raise ValueError("Empty index")
        if self.meta and digest(self.chunks) != self.meta["corpus_hash"]:
            raise ValueError("Index corpus hash mismatch; rebuild the index")
        tokens = [tokenize(c["text"]) for c in self.chunks]
        if not any(tokens):
            raise ValueError("Index has no searchable English or numeric tokens")
        self.bm25 = BM25Okapi(tokens)
        self.emb = self.vector = self.reranker = None
        if self.meta.get("dense"):
            import faiss
            from sentence_transformers import SentenceTransformer
            self.vector = faiss.read_index(str(self.folder / "faiss.index"))
            self.emb = SentenceTransformer(self.meta["embedding"])
            if self.vector.ntotal != len(self.chunks):
                raise ValueError("Vector count mismatch")
        if rerank:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder("BAAI/bge-reranker-base")

    @property
    def mode(self):
        return "hybrid" if self.vector is not None else "bm25"

    def search(self, query, k=5, pool=50, mode=None, issuer=None, as_of=None):
        mode = mode or self.mode
        if mode not in {"bm25", "dense", "hybrid"}:
            raise ValueError("Unknown retrieval mode")
        if mode != "bm25" and self.vector is None:
            raise ValueError("Dense search requested on a sparse index; rebuild with --dense")
        allowed = {i for i, c in enumerate(self.chunks)
                   if (not issuer or c["issuer"].upper() == issuer.upper())
                   and (not as_of or available_as_of(c) <= as_of)}
        if not allowed or k < 1:
            return []
        rankings = []
        if mode in {"bm25", "hybrid"}:
            scores = self.bm25.get_scores(tokenize(query))
            rankings.append(sorted((i for i in allowed if scores[i] > 0), key=lambda i: (-scores[i], i))[:pool])
        if mode in {"dense", "hybrid"}:
            vec = self.emb.encode(["Represent this sentence for searching relevant passages: " + query], normalize_embeddings=True)
            _, ids = self.vector.search(np.asarray(vec, dtype="float32"), len(self.chunks))
            rankings.append([int(i) for i in ids[0] if int(i) in allowed][:pool])
        fused = {}
        for ranking in rankings:
            for rank, i in enumerate(ranking, 1):
                fused[i] = fused.get(i, 0) + 1 / (60 + rank)
        candidates = sorted(fused, key=lambda i: (-fused[i], i))[:max(k, 20)]
        if self.reranker is not None and mode == "hybrid" and candidates:
            scores = self.reranker.predict([(query, self.chunks[i]["text"]) for i in candidates])
            ranked = sorted(zip(candidates, map(float, scores)), key=lambda x: -x[1])
        else:
            ranked = [(i, fused[i]) for i in candidates]
        return [(self.chunks[i], score) for i, score in ranked[:k]]
