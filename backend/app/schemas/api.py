from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class IngestTextRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1)
    source_type: Literal["markdown", "text", "note"] = "text"
    source_uri: str | None = None
    tags: list[str] = []


class IngestUrlRequest(BaseModel):
    url: HttpUrl
    tags: list[str] = []


class DocumentResponse(BaseModel):
    id: str
    title: str
    source_type: str
    source_uri: str | None
    tags: list[str]
    summary: str
    created_at: datetime
    chunk_count: int


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    text: str
    section_path: list[str]
    order_index: int
    page: int | None = None
    tags: list[str]
    token_count: int
    embedding_dimensions: int


class DocumentDetailResponse(DocumentResponse):
    content_preview: str
    content_hash: str
    chunks: list[ChunkResponse]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    intent: Literal["auto", "fact", "concept", "summary", "compare"] = "auto"
    limit: int = Field(default=8, ge=1, le=30)


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    section_path: list[str]
    page: int | None = None
    snippet: str
    score: float


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    section_path: list[str]
    snippet: str
    score: float
    lexical_score: float
    vector_score: float
    rerank_score: float
    tags: list[str]


class AskRequest(SearchRequest):
    answer_mode: Literal["knowledge_only", "draft_with_gaps"] = "knowledge_only"


class AnswerGrounding(BaseModel):
    status: Literal["grounded", "weak", "unsupported"]
    groundedness_score: float
    evidence_coverage: float
    citation_count: int
    unsupported_terms: list[str] = []
    warnings: list[str] = []


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    detected_intent: str
    confidence: float
    grounding: AnswerGrounding | None = None


class QualityIssue(BaseModel):
    kind: str
    severity: Literal["low", "medium", "high"]
    title: str
    description: str
    document_ids: list[str] = []
    confidence: float = 0.0
    evidence: list[str] = []
    suggested_actions: list[str] = []


class TopicCoverage(BaseModel):
    topic: str
    document_count: int
    chunk_count: int
    quality_hint: Literal["thin", "healthy", "dense"]
    related_documents: list[str] = []


class OpsReport(BaseModel):
    generated_at: datetime
    document_count: int
    chunk_count: int
    average_quality_score: float
    issues: list[QualityIssue]
    topic_coverage: list[TopicCoverage]
    faqs: list[dict[str, str]]
    learning_path: list[str]
    graph: dict


class AgentRunRequest(BaseModel):
    objective: str = Field(default="Diagnose knowledge-base quality and suggest operations.", min_length=1)
    focus: Literal["overview", "quality", "conflict", "retrieval", "growth"] = "overview"


class AgentStage(BaseModel):
    name: str
    status: Literal["completed", "needs_attention"]
    observation: str
    evidence: list[str] = []
    next_actions: list[str] = []


class AgentRunResponse(BaseModel):
    objective: str
    focus: str
    generated_at: datetime
    executive_summary: str
    stages: list[AgentStage]
    recommended_backlog: list[dict[str, str]]


class RetrievalEvalRequest(BaseModel):
    queries: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class RetrievalEvalCase(BaseModel):
    query: str
    hit_count: int
    top_score: float
    citation_ready: bool
    recommendation: str


class RetrievalEvalResponse(BaseModel):
    generated_at: datetime
    average_top_score: float
    citation_ready_rate: float
    cases: list[RetrievalEvalCase]


class RuntimeComponent(BaseModel):
    name: str
    status: Literal["ok", "degraded", "action_required"]
    provider: str | None = None
    detail: str
    checks: list[str] = []


class RuntimeStatusResponse(BaseModel):
    generated_at: datetime
    environment: str
    status: Literal["ok", "degraded", "action_required"]
    components: list[RuntimeComponent]
    recommendations: list[str] = []


class TaskResponse(BaseModel):
    id: str
    task_type: str
    status: Literal["queued", "running", "completed", "failed"]
    title: str
    payload: dict
    result: dict | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
