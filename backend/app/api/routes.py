from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from app.core.config import get_settings
from app.schemas.api import (
    AgentRunRequest,
    AgentRunResponse,
    AskRequest,
    AskResponse,
    BenchmarkResponse,
    ChunkResponse,
    CreateBenchmarkRequest,
    DocumentDetailResponse,
    DocumentResponse,
    IngestTextRequest,
    IngestUrlRequest,
    OpsReport,
    RetrievalEvalRequest,
    RetrievalEvalResponse,
    RuntimeStatusResponse,
    SearchHit,
    SearchRequest,
    TaskEventResponse,
    TaskResponse,
)
from app.services.agent import KnowledgeOpsAgent
from app.services.chunking import HierarchicalChunker
from app.services.embedding import EmbeddingService, build_embedding_service
from app.services.evaluation import RetrievalEvaluationService
from app.services.ingestion import IngestionService
from app.services.llm import AnswerGenerator, build_answer_generator
from app.services.ops import KnowledgeOpsService
from app.services.qa import AnswerAgent
from app.services.retrieval import HybridRetrievalService, hit_snippet
from app.services.runtime import RuntimeStatusService
from app.services.security import SecurityValidationError
from app.services.storage import KnowledgeStore
from app.services.tasks import TaskService
from app.services.text_utils import normalize_space, tokenize
from app.services.vector_store import VectorIndex, build_vector_index

router = APIRouter(prefix="/api")


def get_store() -> KnowledgeStore:
    return KnowledgeStore(get_settings().database_url)


def get_embedder() -> EmbeddingService:
    return build_embedding_service(get_settings())


def get_vector_index() -> VectorIndex:
    return build_vector_index(get_settings())


def get_answer_generator() -> AnswerGenerator:
    return build_answer_generator(get_settings())


def get_ingestion(
    store: KnowledgeStore = Depends(get_store),
    embedder: EmbeddingService = Depends(get_embedder),
    vector_index: VectorIndex = Depends(get_vector_index),
) -> IngestionService:
    return IngestionService(store, HierarchicalChunker(embedder), get_settings(), vector_index)


def get_retrieval(
    store: KnowledgeStore = Depends(get_store),
    embedder: EmbeddingService = Depends(get_embedder),
    vector_index: VectorIndex = Depends(get_vector_index),
) -> HybridRetrievalService:
    return HybridRetrievalService(store, embedder, vector_index)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "knowledgeops-agent"}


@router.get("/runtime/status", response_model=RuntimeStatusResponse)
def runtime_status(store: KnowledgeStore = Depends(get_store)):
    return RuntimeStatusService(get_settings(), store).build_status()


@router.post("/documents/text", response_model=DocumentResponse)
def ingest_text(payload: IngestTextRequest, service: IngestionService = Depends(get_ingestion), store: KnowledgeStore = Depends(get_store)):
    doc = service.ingest_text(
        title=payload.title,
        content=payload.content,
        source_type=payload.source_type,
        source_uri=payload.source_uri,
        tags=payload.tags,
    )
    return _document_response(doc, store)


@router.post("/documents/url", response_model=DocumentResponse)
async def ingest_url(payload: IngestUrlRequest, service: IngestionService = Depends(get_ingestion), store: KnowledgeStore = Depends(get_store)):
    if not get_settings().allow_web_ingest:
        raise HTTPException(status_code=403, detail="Web ingestion is disabled.")
    try:
        doc = await service.ingest_url(str(payload.url), payload.tags)
    except SecurityValidationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(doc, store)


@router.post("/documents/upload", response_model=DocumentResponse)
async def ingest_upload(file: UploadFile = File(...), service: IngestionService = Depends(get_ingestion), store: KnowledgeStore = Depends(get_store)):
    raw = await file.read()
    try:
        doc = service.ingest_upload(file.filename or "upload.txt", raw)
    except SecurityValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(doc, store)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(store: KnowledgeStore = Depends(get_store)):
    return [_document_response(doc, store) for doc in store.list_documents()]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, store: KnowledgeStore = Depends(get_store)):
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    chunks = store.list_chunks(document_id)
    return DocumentDetailResponse(
        **_document_response(doc, store).model_dump(),
        content_preview=_content_preview(doc.content),
        content_hash=doc.content_hash,
        chunks=[_chunk_response(chunk) for chunk in chunks],
    )


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkResponse])
def list_document_chunks(document_id: str, store: KnowledgeStore = Depends(get_store)):
    if not store.get_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return [_chunk_response(chunk) for chunk in store.list_chunks(document_id)]


@router.post("/search", response_model=list[SearchHit])
def search(payload: SearchRequest, retrieval: HybridRetrievalService = Depends(get_retrieval)):
    hits = retrieval.search(payload.query, payload.intent, payload.limit)
    return [
        SearchHit(
            chunk_id=hit.chunk.id,
            document_id=hit.document.id,
            title=hit.document.title,
            section_path=hit.chunk.section_path,
            snippet=hit_snippet(hit.chunk.text),
            score=round(hit.score, 4),
            lexical_score=round(hit.lexical_score, 4),
            vector_score=round(hit.vector_score, 4),
            rerank_score=round(hit.rerank_score, 4),
            tags=hit.chunk.tags,
        )
        for hit in hits
    ]


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    retrieval: HybridRetrievalService = Depends(get_retrieval),
    generator: AnswerGenerator = Depends(get_answer_generator),
):
    return AnswerAgent(retrieval, generator).answer(
        payload.query,
        intent=payload.intent,
        limit=payload.limit,
        answer_mode=payload.answer_mode,
    )


@router.get("/ops/report", response_model=OpsReport)
def ops_report(store: KnowledgeStore = Depends(get_store)):
    return KnowledgeOpsService(store).build_report()


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    store: KnowledgeStore = Depends(get_store),
    retrieval: HybridRetrievalService = Depends(get_retrieval),
):
    return KnowledgeOpsAgent(store, retrieval).run(payload.objective, payload.focus)


@router.post("/eval/retrieval", response_model=RetrievalEvalResponse)
def evaluate_retrieval(
    payload: RetrievalEvalRequest,
    store: KnowledgeStore = Depends(get_store),
    retrieval: HybridRetrievalService = Depends(get_retrieval),
):
    return RetrievalEvaluationService(store, retrieval).evaluate(payload.queries, payload.limit)


@router.post("/eval/benchmarks", response_model=BenchmarkResponse)
def create_benchmark(payload: CreateBenchmarkRequest, store: KnowledgeStore = Depends(get_store)):
    benchmark = store.create_benchmark(
        name=payload.name,
        cases=[case.model_dump() for case in payload.cases],
        limit=payload.limit,
    )
    return BenchmarkResponse(**benchmark)


@router.get("/eval/benchmarks", response_model=list[BenchmarkResponse])
def list_benchmarks(limit: int = 30, store: KnowledgeStore = Depends(get_store)):
    return [BenchmarkResponse(**benchmark) for benchmark in store.list_benchmarks(limit)]


@router.post("/eval/benchmarks/{benchmark_id}/run", response_model=RetrievalEvalResponse)
def run_benchmark(
    benchmark_id: str,
    store: KnowledgeStore = Depends(get_store),
    retrieval: HybridRetrievalService = Depends(get_retrieval),
):
    benchmark = store.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found.")
    return RetrievalEvaluationService(store, retrieval).run_benchmark(benchmark)


@router.post("/tasks/ops-report", response_model=TaskResponse)
def create_ops_report_task(
    background_tasks: BackgroundTasks,
    store: KnowledgeStore = Depends(get_store),
):
    service = TaskService(store)
    task = service.create_ops_report_task()
    background_tasks.add_task(service.run_ops_report_task, task["id"])
    return TaskResponse(**task)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(limit: int = 30, store: KnowledgeStore = Depends(get_store)):
    return [TaskResponse(**task) for task in store.list_tasks(limit)]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, store: KnowledgeStore = Depends(get_store)):
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse(**task)


@router.get("/tasks/{task_id}/events", response_model=list[TaskEventResponse])
def list_task_events(task_id: str, store: KnowledgeStore = Depends(get_store)):
    if not store.get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found.")
    return [TaskEventResponse(**event) for event in store.list_task_events(task_id)]


def _document_response(doc, store: KnowledgeStore) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type,
        source_uri=doc.source_uri,
        tags=doc.tags,
        summary=doc.summary,
        created_at=doc.created_at,
        chunk_count=store.count_chunks(doc.id),
    )


def _chunk_response(chunk) -> ChunkResponse:
    return ChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        text=chunk.text,
        section_path=chunk.section_path,
        order_index=chunk.order_index,
        page=chunk.page,
        tags=chunk.tags,
        token_count=len(tokenize(chunk.text)),
        embedding_dimensions=len(chunk.embedding),
    )


def _content_preview(content: str, max_chars: int = 1200) -> str:
    cleaned = normalize_space(content)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
