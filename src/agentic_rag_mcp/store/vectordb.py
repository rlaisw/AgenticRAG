"""LanceDB vector store wrapper.

Chunk ids are `${document_id}:${chunk_index}`; on document change the old
chunks are invalidated (deleted) and new ones inserted (data-model.md).
"""

from __future__ import annotations

from pathlib import Path

CHUNK_SCHEMA_HINT = "id,text,document_id,title,collection,vector"


class VectorStore:
    def __init__(self, path: Path) -> None:
        import lancedb  # deferred: heavy import

        path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(path)

    def _table(self, collection: str, dim: int):
        import pyarrow as pa  # noqa: F401  (lancedb dependency)

        if collection in self._db.table_names():
            return self._db.open_table(collection)
        return self._db.create_table(
            collection,
            schema=__import__("pyarrow").schema(
                [
                    ("id", __import__("pyarrow").string()),
                    ("text", __import__("pyarrow").string()),
                    ("document_id", __import__("pyarrow").string()),
                    ("title", __import__("pyarrow").string()),
                    ("vector", __import__("pyarrow").list_(__import__("pyarrow").float32(), dim)),
                ]
            ),
        )

    @staticmethod
    def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
        """Naive char-window chunker; keeps chunking deterministic for tests."""
        if not text:
            return []
        out, i = [], 0
        while i < len(text):
            out.append(text[i : i + size])
            i += size - overlap
        return out

    def upsert_document(
        self,
        *,
        collection: str,
        document_id: str,
        title: str,
        text: str,
        embedder,
    ) -> int:
        """Invalidate old chunks for document_id, insert fresh ones."""
        chunks = self.chunk_text(text)
        if not chunks:
            self.delete_document(collection, document_id)
            return 0
        vectors = embedder(chunks)
        dim = len(vectors[0])
        table = self._table(collection, dim)
        table.delete(f"document_id = '{document_id}'")
        table.add(
            [
                {
                    "id": f"{document_id}:{i}",
                    "text": chunk,
                    "document_id": document_id,
                    "title": title,
                    "vector": vec,
                }
                for i, (chunk, vec) in enumerate(zip(chunks, vectors))
            ]
        )
        return len(chunks)

    def delete_document(self, collection: str, document_id: str) -> None:
        if collection in self._db.table_names():
            self._db.open_table(collection).delete(f"document_id = '{document_id}'")

    def search(self, collection: str, query_vector, limit: int = 5) -> list[dict]:
        if collection not in self._db.table_names():
            return []
        table = self._db.open_table(collection)
        results = table.search(query_vector).limit(limit).to_list()
        return [
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "title": r["title"],
                "snippet": r["text"][:300],
                "score": float(r.get("_distance", 0.0)),
            }
            for r in results
        ]

    def default_collection(self) -> str:
        names = self._db.table_names()
        return names[0] if names else "default"

    def stats(self) -> dict:
        counts = {}
        for name in self._db.table_names():
            counts[name] = self._db.open_table(name).count_rows()
        return {"collections": counts, "chunks": sum(counts.values())}
