from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from app.models.domain import Chunk, Document


class KnowledgeStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_uri TEXT,
                    tags TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    section_path TEXT NOT NULL,
                    order_index INTEGER NOT NULL,
                    page INTEGER,
                    tags TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                """
            )

    def add_document(self, document: Document, chunks: list[Chunk]) -> Document:
        duplicate = self.find_document_by_hash(document.content_hash)
        if duplicate:
            return duplicate
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents
                (id, title, content, source_type, source_uri, tags, summary, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.content,
                    document.source_type,
                    document.source_uri,
                    json.dumps(document.tags, ensure_ascii=False),
                    document.summary,
                    document.content_hash,
                    document.created_at.isoformat(),
                ),
            )
            conn.executemany(
                """
                INSERT INTO chunks
                (id, document_id, text, section_path, order_index, page, tags, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.text,
                        json.dumps(chunk.section_path, ensure_ascii=False),
                        chunk.order_index,
                        chunk.page,
                        json.dumps(chunk.tags, ensure_ascii=False),
                        json.dumps(chunk.embedding),
                    )
                    for chunk in chunks
                ],
            )
        return document

    def find_document_by_hash(self, content_hash: str) -> Document | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE content_hash = ? LIMIT 1", (content_hash,)
            ).fetchone()
        return self._row_to_document(row) if row else None

    def list_documents(self) -> list[Document]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [self._row_to_document(row) for row in rows]

    def list_chunks(self) -> list[Chunk]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chunks ORDER BY document_id, order_index").fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def count_chunks(self, document_id: str | None = None) -> int:
        with self._connect() as conn:
            if document_id:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM chunks WHERE document_id = ?", (document_id,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        return int(row["n"])

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            source_type=row["source_type"],
            source_uri=row["source_uri"],
            tags=json.loads(row["tags"]),
            summary=row["summary"],
            content_hash=row["content_hash"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_chunk(self, row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=row["id"],
            document_id=row["document_id"],
            text=row["text"],
            section_path=json.loads(row["section_path"]),
            order_index=row["order_index"],
            page=row["page"],
            tags=json.loads(row["tags"]),
            embedding=json.loads(row["embedding"]),
        )

