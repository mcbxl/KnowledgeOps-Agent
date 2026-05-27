from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine, RowMapping

from app.models.domain import Chunk, Document


metadata = MetaData()

documents_table = Table(
    "documents",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("title", String(240), nullable=False),
    Column("content", Text, nullable=False),
    Column("source_type", String(64), nullable=False),
    Column("source_uri", String(1024)),
    Column("tags", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("content_hash", String(128), nullable=False, index=True),
    Column("created_at", String(64), nullable=False),
)

chunks_table = Table(
    "chunks",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("document_id", String(64), ForeignKey("documents.id"), nullable=False, index=True),
    Column("text", Text, nullable=False),
    Column("section_path", Text, nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("page", Integer),
    Column("tags", Text, nullable=False),
    Column("embedding", Text, nullable=False),
)


class KnowledgeStore:
    """SQLAlchemy-backed metadata store.

    Production is configured through a MySQL URL. Tests can still inject a SQLite
    URL because the repository should be testable without a local MySQL daemon.
    """

    def __init__(self, database_url: str | Path) -> None:
        if isinstance(database_url, Path):
            database_url = f"sqlite:///{database_url}"
        self.database_url = str(database_url)
        self.engine = self._create_engine(self.database_url)
        metadata.create_all(self.engine)

    def _create_engine(self, database_url: str) -> Engine:
        kwargs = {"future": True, "pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        return create_engine(database_url, **kwargs)

    def add_document(self, document: Document, chunks: list[Chunk]) -> Document:
        duplicate = self.find_document_by_hash(document.content_hash)
        if duplicate:
            return duplicate
        with self.engine.begin() as conn:
            conn.execute(
                documents_table.insert().values(
                    id=document.id,
                    title=document.title,
                    content=document.content,
                    source_type=document.source_type,
                    source_uri=document.source_uri,
                    tags=json.dumps(document.tags, ensure_ascii=False),
                    summary=document.summary,
                    content_hash=document.content_hash,
                    created_at=document.created_at.isoformat(),
                )
            )
            if chunks:
                conn.execute(
                    chunks_table.insert(),
                    [
                        {
                            "id": chunk.id,
                            "document_id": chunk.document_id,
                            "text": chunk.text,
                            "section_path": json.dumps(chunk.section_path, ensure_ascii=False),
                            "order_index": chunk.order_index,
                            "page": chunk.page,
                            "tags": json.dumps(chunk.tags, ensure_ascii=False),
                            "embedding": json.dumps(chunk.embedding),
                        }
                        for chunk in chunks
                    ],
                )
        return document

    def find_document_by_hash(self, content_hash: str) -> Document | None:
        statement = select(documents_table).where(documents_table.c.content_hash == content_hash).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(statement).mappings().first()
        return self._row_to_document(row) if row else None

    def list_documents(self) -> list[Document]:
        statement = select(documents_table).order_by(documents_table.c.created_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_document(row) for row in rows]

    def list_chunks(self) -> list[Chunk]:
        statement = select(chunks_table).order_by(chunks_table.c.document_id, chunks_table.c.order_index)
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_chunk(row) for row in rows]

    def count_chunks(self, document_id: str | None = None) -> int:
        statement = select(func.count()).select_from(chunks_table)
        if document_id:
            statement = statement.where(chunks_table.c.document_id == document_id)
        with self.engine.connect() as conn:
            return int(conn.execute(statement).scalar_one())

    def _row_to_document(self, row: RowMapping) -> Document:
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

    def _row_to_chunk(self, row: RowMapping) -> Chunk:
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
