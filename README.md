# KnowledgeOps Agent：个人知识库运营与推理 Agent

KnowledgeOps Agent 是一个面向个人/团队知识库的智能运营系统。它不是简单的“上传文档然后问答”的 RAG Demo，而是围绕知识资产生命周期构建：多源接入、结构化解析、层级化切分、混合检索、引用溯源问答、质量诊断、冲突检测、主题覆盖分析、知识图谱和 Agent 治理工作流。

## 核心能力

- **多源知识接入**：支持 Markdown、纯文本、网页链接、文件上传，PDF 解析通过可选依赖扩展。
- **结构化解析与元数据管理**：自动生成摘要、标签、内容哈希，并为 chunk 绑定来源、章节路径、顺序和标签。
- **层级化 Chunking**：按标题层级和段落语义边界切分，保留章节路径，提升长文档检索上下文完整性。
- **Hybrid Search**：融合 BM25 风格关键词召回、本地确定性 embedding 向量召回和 rerank 分数。
- **问题意图识别**：根据事实、概念、总结、对比类问题动态调整关键词、向量和 rerank 权重。
- **引用溯源问答**：回答只基于知识库片段，并返回文档名、章节路径、原文片段和相关度分数。
- **文档检查器**：支持查看单篇文档的正文预览、内容哈希、chunk 列表、章节路径、标签、Token 数和 embedding 维度。
- **LangGraph Agent 工作流**：使用 `StateGraph` 编排资产盘点、质量诊断、冲突检测、检索探测和治理计划节点。
- **证据化运营报告**：对重复、低质量、冲突候选问题输出置信度、证据片段和建议动作。
- **Topic Coverage**：识别薄弱主题、健康主题和高密度主题，用于知识补全和学习路线生成。
- **检索评估台**：输入 benchmark queries，评估 TopK 命中、Top1 分数和引用元数据完整性。
- **运营任务中心**：支持触发 KnowledgeOps 报告任务并查看任务状态，为后续接入 Celery/RQ 预留边界。
- **知识图谱**：展示 document、section、topic 三类节点及其关系。

## 技术栈

- 前端：React、Vite、React Flow、Lucide Icons
- 后端：FastAPI、Pydantic、SQLAlchemy、MySQL
- 文档解析：BeautifulSoup、可选 PyMuPDF
- 检索：BM25 风格关键词评分、确定性 embedding、启发式 rerank
- Agent：LangGraph `StateGraph`
- 存储：MySQL 元数据主库，后续可扩展 Qdrant + Elasticsearch/Meilisearch

## 目录结构

```text
backend/        FastAPI 后端、检索链路、问答 Agent、LangGraph Agent
frontend/       React/Vite 前端工作台
docs/           中文架构说明、简历描述、后续开发计划
samples/        本地测试用样例知识文档
docker-compose.yml  MySQL 本地开发环境
```

## 快速启动

### 1. 启动 MySQL

```powershell
cd D:\Code\KnowledgeOps-Agent
docker compose up -d mysql
```

默认数据库连接串：

```text
mysql+pymysql://knowledgeops:knowledgeops@127.0.0.1:3306/knowledgeops?charset=utf8mb4
```

可在 `backend/.env` 覆盖：

```text
KNOWLEDGEOPS_DATABASE_URL=mysql+pymysql://user:password@host:3306/knowledgeops?charset=utf8mb4
```

### 2. 启动后端

```powershell
cd D:\Code\KnowledgeOps-Agent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如需 PDF 解析：

```powershell
pip install -e ".[pdf]"
```

### 3. 启动前端

```powershell
cd D:\Code\KnowledgeOps-Agent\frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

后端健康检查：

```text
http://127.0.0.1:8000/api/health
```

## API 概览

- `POST /api/documents/text`：导入文本或 Markdown
- `POST /api/documents/url`：导入网页
- `POST /api/documents/upload`：上传本地文件
- `GET /api/documents`：查看文档列表
- `GET /api/documents/{document_id}`：查看文档详情和 chunk 结构
- `GET /api/documents/{document_id}/chunks`：查看单篇文档的 chunk 列表
- `POST /api/search`：Hybrid Search 检索
- `POST /api/ask`：引用溯源问答
- `GET /api/ops/report`：生成知识库运营报告
- `POST /api/agent/run`：运行 LangGraph KnowledgeOps Agent 工作流
- `POST /api/eval/retrieval`：执行检索链路评估
- `POST /api/tasks/ops-report`：创建运营报告任务
- `GET /api/tasks`：查看任务列表
- `GET /api/tasks/{task_id}`：查看任务详情

## 当前版本的工程亮点

- 使用 MySQL 作为元数据主库，SQLAlchemy 封装存储边界。
- 使用 LangGraph `StateGraph` 编排 Agent 节点，工作流阶段可观测、可扩展。
- 检索链路返回 BM25、Vector、Rerank 三类分数，便于解释召回依据。
- 文档检查器可直接展示 chunking 结果和索引元数据，方便演示“不是简单切文本”。
- 运营报告中的每个 issue 都带 `confidence`、`evidence` 和 `suggested_actions`。
- 任务中心以 `tasks` 表记录运营任务状态，后续可替换为 Celery/RQ + Redis。
- 知识图谱同时展示 document、section、topic 三类节点。
- 检索评估接口可作为后续 RAGAS 或自定义 benchmark 的入口。

## 后续升级方向

1. 接入 Qdrant/Milvus 作为向量数据库。
2. 接入 Elasticsearch/Meilisearch 作为关键词索引。
3. 增加 Alembic migration 管理 MySQL 表结构演进。
4. 使用 bge-reranker、Jina Reranker 或 Cohere Rerank 替换启发式 rerank。
5. 引入 Celery/RQ + Redis，将文档解析、索引构建和运营报告改为异步任务。
6. 增加 RAGAS 或自定义 benchmark，评估召回率、引用覆盖率和答案忠实度。
