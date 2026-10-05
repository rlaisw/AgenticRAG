"""Local embedding service (sentence-transformers)."""

from __future__ import annotations


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer  # deferred heavy import

        self._model = SentenceTransformer(model_name, device=device)
        self.dim = self._model.get_sentence_embedding_dimension()

    def __call__(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.encode(list(texts), show_progress_bar=False)]
