"""Embedding-based retrieval of historically resolved support threads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.config import EMBEDDING_MODEL, PROCESSED_DIR, TOP_K_PRECEDENTS


@dataclass
class Precedent:
    id: str
    customer_msg: str
    brand_reply: str
    similarity: float
    resolved: bool = True


class PrecedentRetriever:
    """Retrieve similar resolved (customer, reply) pairs via sentence embeddings."""

    def __init__(self, precedents: list[dict] | None = None) -> None:
        self.precedents: list[dict] = precedents or []
        self.embeddings: np.ndarray | None = None
        self._model = None

    @classmethod
    def from_processed(cls) -> "PrecedentRetriever":
        path = PROCESSED_DIR / "precedents.json"
        if not path.exists():
            raise FileNotFoundError(
                f"No precedents at {path}. Run: python scripts/prepare_data.py"
            )
        with path.open(encoding="utf-8") as f:
            precedents = json.load(f)
        retriever = cls(precedents)
        retriever.build_index()
        return retriever

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def build_index(self) -> None:
        if not self.precedents:
            self.embeddings = np.array([])
            return
        model = self._load_model()
        texts = [p["customer_msg"] for p in self.precedents]
        self.embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def retrieve(self, query: str, top_k: int = TOP_K_PRECEDENTS) -> list[Precedent]:
        if not self.precedents or self.embeddings is None or len(self.embeddings) == 0:
            return []

        model = self._load_model()
        query_emb = model.encode([query], normalize_embeddings=True)[0]

        # Cosine similarity (embeddings are normalized)
        scores = self.embeddings @ query_emb
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            p = self.precedents[idx]
            sim = float(scores[idx])
            results.append(Precedent(
                id=p["id"],
                customer_msg=p["customer_msg"],
                brand_reply=p["brand_reply"],
                similarity=sim,
                resolved=p.get("resolved", True),
            ))
        return results

    def best_similarity(self, query: str) -> float:
        results = self.retrieve(query, top_k=1)
        return results[0].similarity if results else 0.0

    def precedents_to_prompt_format(self, precedents: list[Precedent]) -> str:
        return json.dumps([
            {
                "id": p.id,
                "similarity": round(p.similarity, 3),
                "customer_msg": p.customer_msg,
                "brand_reply": p.brand_reply,
                "resolved": p.resolved,
            }
            for p in precedents
        ], indent=2)
