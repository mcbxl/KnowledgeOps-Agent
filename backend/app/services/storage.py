from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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
    update,
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

tasks_table = Table(
    "tasks",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("task_type", String(80), nullable=False, index=True),
    Column("status", String(32), nullable=False, index=True),
    Column("title", String(240), nullable=False),
    Column("payload", Text, nullable=False),
    Column("result", Text),
    Column("error", Text),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

task_events_table = Table(
    "task_events",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("task_id", String(64), ForeignKey("tasks.id"), nullable=False, index=True),
    Column("event_type", String(80), nullable=False, index=True),
    Column("message", String(500), nullable=False),
    Column("payload", Text, nullable=False),
    Column("created_at", String(64), nullable=False),
)

benchmarks_table = Table(
    "retrieval_benchmarks",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(160), nullable=False, index=True),
    Column("cases", Text, nullable=False),
    Column("limit", Integer, nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
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

    def get_document(self, document_id: str) -> Document | None:
        statement = select(documents_table).where(documents_table.c.id == document_id).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(statement).mappings().first()
        return self._row_to_document(row) if row else None

    def list_documents(self) -> list[Document]:
        statement = select(documents_table).order_by(documents_table.c.created_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_document(row) for row in rows]

    def list_chunks(self, document_id: str | None = None) -> list[Chunk]:
        statement = select(chunks_table).order_by(chunks_table.c.document_id, chunks_table.c.order_index)
        if document_id:
            statement = statement.where(chunks_table.c.document_id == document_id)
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_chunk(row) for row in rows]

    def count_chunks(self, document_id: str | None = None) -> int:
        statement = select(func.count()).select_from(chunks_table)
        if document_id:
            statement = statement.where(chunks_table.c.document_id == document_id)
        with self.engine.connect() as conn:
            return int(conn.execute(statement).scalar_one())

    def create_task(self, task_type: str, title: str, payload: dict | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        task = {
            "id": str(uuid4()),
            "task_type": task_type,
            "status": "queued",
            "title": title,
            "payload": json.dumps(payload or {}, ensure_ascii=False),
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(tasks_table.insert().values(**task))
        self.add_task_event(task["id"], "queued", f"Task queued: {title}", payload or {})
        return self._row_to_task(task)

    def update_task(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> dict | None:
        values = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "result": json.dumps(result, ensure_ascii=False) if result is not None else None,
            "error": error,
        }
        statement = update(tasks_table).where(tasks_table.c.id == task_id).values(**values)
        with self.engine.begin() as conn:
            conn.execute(statement)
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict | None:
        statement = select(tasks_table).where(tasks_table.c.id == task_id).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(statement).mappings().first()
        return self._row_to_task(row) if row else None

    def list_tasks(self, limit: int = 30) -> list[dict]:
        statement = select(tasks_table).order_by(tasks_table.c.created_at.desc()).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_task(row) for row in rows]

    def add_task_event(
        self,
        task_id: str,
        event_type: str,
        message: str,
        payload: dict | None = None,
    ) -> dict:
        event = {
            "id": str(uuid4()),
            "task_id": task_id,
            "event_type": event_type,
            "message": message,
            "payload": json.dumps(payload or {}, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.engine.begin() as conn:
            conn.execute(task_events_table.insert().values(**event))
        return self._row_to_task_event(event)

    def list_task_events(self, task_id: str) -> list[dict]:
        statement = (
            select(task_events_table)
            .where(task_events_table.c.task_id == task_id)
            .order_by(task_events_table.c.created_at.asc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_task_event(row) for row in rows]

    def create_benchmark(self, name: str, cases: list[dict], limit: int = 5) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        benchmark = {
            "id": str(uuid4()),
            "name": name,
            "cases": json.dumps(cases, ensure_ascii=False),
            "limit": limit,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(benchmarks_table.insert().values(**benchmark))
        return self._row_to_benchmark(benchmark)

    def list_benchmarks(self, limit: int = 30) -> list[dict]:
        statement = select(benchmarks_table).order_by(benchmarks_table.c.updated_at.desc()).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return [self._row_to_benchmark(row) for row in rows]

    def get_benchmark(self, benchmark_id: str) -> dict | None:
        statement = select(benchmarks_table).where(benchmarks_table.c.id == benchmark_id).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(statement).mappings().first()
        return self._row_to_benchmark(row) if row else None

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

    def _row_to_task(self, row) -> dict:
        return {
            "id": row["id"],
            "task_type": row["task_type"],
            "status": row["status"],
            "title": row["title"],
            "payload": json.loads(row["payload"] or "{}"),
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"]),
        }

    def _row_to_benchmark(self, row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "cases": json.loads(row["cases"] or "[]"),
            "limit": row["limit"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"]),
        }

    def _row_to_task_event(self, row) -> dict:
        return {
            "id": row["id"],
            "task_id": row["task_id"],
            "event_type": row["event_type"],
            "message": row["message"],
            "payload": json.loads(row["payload"] or "{}"),
            "created_at": datetime.fromisoformat(row["created_at"]),
        }
