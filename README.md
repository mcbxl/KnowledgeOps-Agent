# KnowledgeOps Agent

个人知识库运营与推理 Agent。它不是只做“上传文档然后问答”的 RAG Demo，而是围绕知识资产生命周期构建：多源接入、层级化 chunking、真实 Embedding/LLM 接入、Qdrant 向量索引、Hybrid Search、引用溯源问答、质量诊断、冲突检测、Topic Coverage、检索评测和 LangGraph 治理工作流。

## 核心能力

- 多源知识接入：Markdown、纯文本、网页链接、文件上传，PDF 解析可通过 optional extras 启用。
- 层级化 Chunking：按标题层级和段落语义边界切分，保留章节路径、来源、顺序和标签。
- 真实 Embedding 接入：默认本地 deterministic embedding；生产可切换 LangChain `OpenAIEmbeddings`。
- Qdrant 向量数据库：文档入库时同步 upsert chunk vectors，检索时参与 hybrid scoring。
- Hybrid Search：融合 BM25 风格关键词召回、向量召回和 rerank 分数。
- LLM 答案生成：默认本地引用答案生成器；生产可切换 LangChain `ChatOpenAI`，只基于召回上下文回答。
- Grounding Audit：对答案和引用片段做轻量 faithful 检查，返回 groundedness、evidence coverage、unsupported terms 和风险提示。
- LangGraph Agent：使用 `StateGraph` 编排资产盘点、质量诊断、冲突检测、检索探测和治理计划。
- Runtime Readiness：检查 MySQL/SQLite、Embedding、LLM、Qdrant、安全配置的生产就绪状态。
- 生产安全：URL SSRF 风险拦截、上传大小/扩展名限制、环境变量配置 CORS 和模型密钥。
- 测试覆盖：API smoke、安全校验、本地 LLM fallback、向量索引参与检索。

## 技术栈

- Frontend：React、Vite、React Flow、Lucide Icons
- Backend：FastAPI、Pydantic、SQLAlchemy、MySQL
- Agent：LangGraph `StateGraph`
- Model Layer：LangChain OpenAIEmbeddings、LangChain ChatOpenAI、本地 deterministic fallback
- Vector DB：Qdrant，可降级为数据库内 JSON embedding 余弦检索
- Test：pytest、ruff

## 快速启动

### 1. 启动 MySQL 和 Qdrant

```powershell
docker compose up -d mysql qdrant
```

### 2. 配置后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

启用真实模型和 Qdrant 时安装生产 extras：

```powershell
pip install -e .[prod]
```

复制 `backend/.env.example` 为 `backend/.env`，按需配置：

```text
KNOWLEDGEOPS_EMBEDDING_PROVIDER=openai
KNOWLEDGEOPS_LLM_PROVIDER=openai
OPENAI_API_KEY=...
KNOWLEDGEOPS_ENABLE_QDRANT=true
KNOWLEDGEOPS_QDRANT_URL=http://127.0.0.1:6333
```

不配置这些变量时，系统使用本地 fallback，适合无 API Key 的开发和测试。

### 3. 启动后端

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

## API 概览

- `POST /api/documents/text`：导入文本或 Markdown
- `POST /api/documents/url`：导入网页
- `POST /api/documents/upload`：上传本地文件
- `GET /api/documents`：查看文档列表
- `GET /api/documents/{document_id}`：查看文档详情和 chunk 结构
- `POST /api/search`：Hybrid Search 检索
- `POST /api/ask`：引用溯源问答，并返回 Grounding Audit
- `GET /api/ops/report`：生成知识库运营报告
- `POST /api/agent/run`：运行 LangGraph KnowledgeOps Agent
- `GET /api/runtime/status`：查看模型、向量库、数据库和安全配置的运行状态
- `POST /api/eval/retrieval`：执行检索链路评测
- `POST /api/tasks/ops-report`：创建运营报告任务
- `GET /api/tasks`：查看任务列表

## 验证

```powershell
cd backend
python -m pytest
python -m ruff check .
```

当前测试覆盖导入、检索、问答、Grounding Audit、LangGraph Agent、检索评测、任务中心、Runtime Readiness、安全校验和向量索引融合路径。
