"""Small local RAG index: sentence-transformers + FAISS, with lexical fallback."""
from pathlib import Path
import re

DOC_DIR = Path(__file__).resolve().parents[2] / "reference_documents"


def load_chunks() -> list[dict]:
    chunks = []
    for path in DOC_DIR.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        # Simple paragraph chunking is easy to explain and sufficient for this MVP.
        for paragraph in [p.strip() for p in text.split("\n\n") if p.strip()]:
            chunks.append({"text": paragraph, "source": path.name})
    return chunks


def retrieve_medical_evidence(query: str, k: int = 4) -> list[dict]:
    chunks = load_chunks()
    if not chunks:
        return []
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
        import numpy as np
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        vectors = model.encode([x["text"] for x in chunks], normalize_embeddings=True)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(np.asarray(vectors, dtype="float32"))
        query_vector = model.encode([query], normalize_embeddings=True)
        scores, ids = index.search(np.asarray(query_vector, dtype="float32"), min(k, len(chunks)))
        return [{**chunks[int(i)], "score": round(float(s), 3), "method": "FAISS + Sentence Transformers"}
                for s, i in zip(scores[0], ids[0]) if i >= 0 and s > 0.15]
    except Exception:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = []
        for chunk in chunks:
            words = set(re.findall(r"[a-z0-9]+", chunk["text"].lower()))
            score = len(terms & words) / max(1, len(terms))
            if score:
                ranked.append({**chunk, "score": round(score, 3), "method": "local lexical fallback"})
        return sorted(ranked, key=lambda x: x["score"], reverse=True)[:k]
