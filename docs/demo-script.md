# Demo Script

This script is designed for a 6-8 minute interview or portfolio walkthrough. It shows that KnowledgeOps Agent is not a simple RAG demo, but a knowledge-base operations agent with retrieval quality, grounding, runtime readiness, and governance workflows.

## 1. Positioning

Open with:

> KnowledgeOps Agent is a personal knowledge-base operations system. It combines RAG, LangGraph workflows, Qdrant vector search, grounded answer generation, retrieval benchmarks, and production guardrails. The goal is not only to answer questions, but to diagnose and govern the knowledge base over time.

Key points to mention:

- Multi-source ingestion
- Hierarchical chunking with metadata
- Hybrid retrieval with lexical, vector, and rerank scores
- Grounded answers with citations
- LangGraph governance workflow
- Runtime readiness and production safety
- Retrieval benchmarks and task timelines

## 2. Start The Stack

```powershell
docker compose up -d mysql qdrant

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## 3. Ingest

Go to the Ingest tab.

Use the default React 18 migration note, or paste a small knowledge document:

```markdown
# React 18 Migration

React 18 recommends createRoot for new roots.

## Legacy API

ReactDOM.render is legacy guidance and should not be used for new React 18 roots.
```

Show:

- Document list
- Document inspector
- Chunk text
- Section path
- Token count
- Embedding dimensions

Talking point:

> The chunker preserves document structure. Retrieval citations can point back to document title and section path, not just anonymous text slices.

## 4. Search

Go to Search.

Query:

```text
React createRoot
```

Show:

- Top hits
- Score
- BM25 score
- Vector score
- Rerank score

Talking point:

> The retrieval pipeline is inspectable. I expose lexical, vector, and rerank scores so retrieval behavior can be debugged instead of treated as a black box.

## 5. Ask With Grounding Audit

Go to Ask.

Question:

```text
Which rendering API should React 18 use?
```

Show:

- Answer
- Citations
- Confidence
- Grounding status
- Groundedness score
- Evidence coverage
- Unsupported terms

Talking point:

> The answer is not just generated. It is audited against citation snippets with a lightweight grounding check. This gives a first guardrail before adding heavier RAGAS or LLM-as-judge evaluation.

## 6. Runtime

Go to Runtime.

Show:

- Metadata Store
- Embedding Model
- Answer Generator
- Vector Index
- Security Guardrails

Talking point:

> Runtime Readiness shows whether the project is running in local fallback mode or production mode. It explicitly checks model providers, Qdrant, database connectivity, API key state, and upload/web-ingest guardrails.

## 7. Agent

Go to Agent.

Run with:

```text
Diagnose knowledge-base quality and generate governance actions.
```

Show workflow stages:

- Asset inventory
- Quality diagnosis
- Conflict detection
- Retrieval probe
- Governance plan

Talking point:

> LangGraph turns the governance flow into observable nodes. Each stage returns evidence and next actions, so the system can operate the knowledge base, not only answer from it.

## 8. Evaluation

Go to Eval.

Queries:

```text
React createRoot
ReactDOM.render
React 18 migration
```

Click Evaluate, then Save Benchmark.

Show:

- Average top score
- Citation-ready rate
- Saved benchmarks
- Re-run benchmark

Talking point:

> Saved benchmarks give a regression baseline. If chunking, embeddings, rerank weights, or prompts change, I can re-run the same benchmark and compare quality.

## 9. Tasks

Go to Tasks.

Click Generate Ops Report.

Show:

- Task status
- Result summary
- Timeline events

Talking point:

> The current executor is FastAPI BackgroundTasks, but the API and data model already preserve task state and task events, so Celery/RQ can replace the executor without changing the frontend contract.

## 10. Close

Close with:

> The interesting part of this project is the operational layer around RAG: runtime readiness, grounding audit, retrieval benchmark, task timeline, and LangGraph governance. These are the pieces I would expect in a production knowledge-agent system.
