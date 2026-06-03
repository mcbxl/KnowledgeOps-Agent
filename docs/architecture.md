# 系统架构设计

## 项目定位

KnowledgeOps Agent 面向个人或团队知识库，目标不是简单 RAG Demo，而是持续运营知识资产。系统通过文档接入、结构化切分、真实模型接入、向量数据库、混合检索、引用问答、冲突检测和治理建议，让知识库具备自我诊断和主动维护能力。

## 总体架构

```text
Frontend React/Vite
  -> 文档导入、文档检查器、检索、问答、运营报告、Agent 工作流、检索评测

FastAPI Backend
  -> Ingestion Service
  -> Hierarchical Chunker
  -> Embedding Provider
       -> local deterministic embedding
       -> LangChain OpenAIEmbeddings
  -> Vector Index
       -> local JSON embedding fallback
       -> Qdrant collection
  -> Hybrid Retrieval
       -> BM25-style lexical score
       -> vector score
       -> heuristic rerank score
  -> Answer Agent
       -> local citation generator
       -> LangChain ChatOpenAI grounded generation
  -> LangGraph KnowledgeOps Agent
  -> Evaluation / Task / Ops Services

Storage
  -> MySQL: documents, chunks, tasks, metadata
  -> Qdrant: chunk vectors and retrieval payload
```

## 模型接入

模型层使用 Provider 模式。默认 `local` provider 使用确定性 embedding 和本地引用答案生成器，保证测试无需 API Key、结果可复现。生产环境可通过环境变量切换：

```text
KNOWLEDGEOPS_EMBEDDING_PROVIDER=openai
KNOWLEDGEOPS_EMBEDDING_MODEL=text-embedding-3-small
KNOWLEDGEOPS_LLM_PROVIDER=openai
KNOWLEDGEOPS_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

真实模型接入通过 LangChain：

- `LangChainOpenAIEmbeddingService` 使用 `langchain_openai.OpenAIEmbeddings`
- `LangChainOpenAIAnswerGenerator` 使用 `langchain_openai.ChatOpenAI`
- 答案生成系统提示要求只基于召回上下文回答，并输出引用标记

## 向量数据库集成

系统支持 Qdrant 作为生产级向量索引：

```text
KNOWLEDGEOPS_ENABLE_QDRANT=true
KNOWLEDGEOPS_QDRANT_URL=http://127.0.0.1:6333
KNOWLEDGEOPS_QDRANT_COLLECTION=knowledgeops_chunks
```

文档入库时，chunk embedding 写入 MySQL 的同时会同步 upsert 到 Qdrant。检索时，`HybridRetrievalService` 先生成 query embedding，再从 Qdrant 取向量候选分数，并与 BM25 风格关键词分数、rerank 分数融合。

未启用 Qdrant 时，系统使用 MySQL/SQLite 中保存的 chunk embedding 进行本地余弦相似度计算，因此开发和测试环境不依赖外部服务。

## LangGraph Agent 工作流

`KnowledgeOpsAgent` 使用 LangGraph `StateGraph` 编排，每个阶段是一个 graph node，共享 `AgentState`，通过 `compile().invoke()` 执行：

1. Asset inventory：统计文档、chunk 和质量分。
2. Quality diagnosis：识别低质量文档候选。
3. Conflict detection：识别版本迁移、废弃 API、互斥结论等冲突候选。
4. Retrieval probe：用主题词检查检索链路健康度。
5. Governance plan：生成治理动作和 backlog。

每个阶段输出 `status`、`observation`、`evidence` 和 `next_actions`，方便前端展示和面试演示。

## 安全与测试

生产安全边界包括：

- URL 接入只允许 `http/https`，默认拦截 localhost、loopback、private IP、link-local、reserved IP，降低 SSRF 风险。
- 文件上传限制最大字节数和扩展名，默认仅允许 `txt/md/markdown/pdf`。
- CORS 来源通过 `KNOWLEDGEOPS_CORS_ORIGINS` 配置，避免硬编码生产域名。
- 模型 API Key 只通过环境变量读取，不写入代码或响应。

测试覆盖包括：

- API smoke test：导入、检索、问答、Agent、评测、任务中心。
- 安全测试：私有 URL、非法扩展名、超大上传拦截。
- Provider 测试：本地答案生成器可复现、向量索引分数参与 hybrid retrieval。

运行：

```powershell
cd backend
python -m pip install -e .[dev]
python -m pytest
python -m ruff check .
```
