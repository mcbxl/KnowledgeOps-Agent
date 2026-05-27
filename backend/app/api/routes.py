from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.core.config import get_settings
from app.schemas.api import (
    AgentRunRequest,
    AgentRunResponse,
    AskRequest,
    AskResponse,
    DocumentResponse,
    IngestTextRequest,
    IngestUrlRequest,
    OpsReport,
    RetrievalEvalRequest,
    RetrievalEvalResponse,
    SearchHit,
    SearchRequest,
)
from app.services.agent import KnowledgeOpsAgent
from app.services.chunking import HierarchicalChunker
from app.services.embedding import DeterministicEmbeddingService
from app.services.evaluation import RetrievalEvaluationService
from app.services.ingestion import IngestionService
from app.services.ops import KnowledgeOpsService
from app.services.qa import AnswerAgent
from app.services.retrieval import HybridRetrievalService, hit_snippet
from app.services.storage import KnowledgeStore

router = APIRouter(prefix="/api")


def get_store() -> KnowledgeStore:
    return KnowledgeStore(get_settings().db_path)


def get_embedder() -> DeterministicEmbeddingService:
    return DeterministicEmbeddingService()


def get_ingestion(
    store: KnowledgeStore = Depends(get_store),
    embedder: DeterministicEmbeddingService = Depends(get_embedder),
) -> IngestionService:
    return IngestionService(store, HierarchicalChunker(embedder))


def get_retrieval(
    store: KnowledgeStore = Depends(get_store),
    embedder: DeterministicEmbeddingService = Depends(get_embedder),
) -> HybridRetrievalService:
    return HybridRetrievalService(store, embedder)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "knowledgeops-agent"}


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
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(doc, store)


@router.post("/documents/upload", response_model=DocumentResponse)
async def ingest_upload(file: UploadFile = File(...), service: IngestionService = Depends(get_ingestion), store: KnowledgeStore = Depends(get_store)):
    raw = await file.read()
    try:
        doc = service.ingest_upload(file.filename or "upload.txt", raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(doc, store)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(store: KnowledgeStore = Depends(get_store)):
    return [_document_response(doc, store) for doc in store.list_documents()]


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
def ask(payload: AskRequest, retrieval: HybridRetrievalService = Depends(get_retrieval)):
    return AnswerAgent(retrieval).answer(
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
