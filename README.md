# KnowledgeOps Agent：个人知识库运营与推理 Agent

KnowledgeOps Agent 不是普通的“上传文档然后问答”系统，而是面向个人或团队知识库的智能运营 Agent。系统支持多源知识接入、层级化切分、Hybrid Search、Rerank、引用溯源问答、知识质量诊断、冲突检测、FAQ 生成、学习路线生成和知识图谱构建，目标是把知识库从被动检索工具升级为主动治理系统。

## 核心能力

- **多源知识接入**：支持 Markdown、纯文本、网页链接、文件上传，PDF 解析预留可选依赖。
- **结构化解析与元数据管理**：自动生成摘要、标签、内容哈希，并为 chunk 绑定文档来源、章节路径、顺序和标签。
- **层级化 Chunking**：按 Markdown 标题层级和段落语义边界切分，保留章节路径，提升长文档检索上下文完整性。
- **Hybrid Search**：融合 BM25 风格关键词召回、本地确定性 embedding 向量召回和 rerank 分数。
- **问题意图识别**：根据问题类型动态调整关键词、向量、rerank 权重，支持事实、概念、总结和对比类查询。
- **引用溯源问答**：回答只基于知识库片段，并返回文档名、章节路径、原文片段和相关度分数。
- **KnowledgeOps Agent**：执行资产盘点、质量诊断、冲突检测、检索探测和治理计划生成。
- **运营报告**：自动输出重复候选、低质量文档、潜在冲突、FAQ、学习路线和知识图谱数据。
- **前端工作台**：提供导入、检索、问答、运营报告、Agent 工作流和知识图谱视图。

## 技术栈

- 前端：React、Vite、React Flow、Lucide Icons
- 后端：FastAPI、Pydantic、SQLite
- 文档解析：BeautifulSoup、可选 PyMuPDF
- 检索：BM25 风格关键词评分、确定性 embedding、启发式 rerank
- Agent：本地规则编排，接口边界可升级为 LangGraph
- 存储：本地 SQLite，后续可替换为 PostgreSQL + Qdrant + Elasticsearch/Meilisearch

## 目录结构

```text
backend/        FastAPI 后端、检索链路、问答 Agent、KnowledgeOps Agent
frontend/       React/Vite 前端工作台
docs/           中文架构说明、简历描述、后续开发计划
samples/        本地测试用样例知识文档
```

## 快速启动

### 1. 启动后端

```powershell
cd D:\Code\KnowledgeOps-Agent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果需要 PDF 解析能力：

```powershell
pip install -e ".[pdf]"
```

### 2. 启动前端

```powershell
cd D:\Code\KnowledgeOps-Agent\frontend
npm install
npm run dev
```

浏览器访问 Vite 输出的地址，默认是：

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
- `POST /api/search`：Hybrid Search 检索
- `POST /api/ask`：引用溯源问答
- `GET /api/ops/report`：生成知识库运营报告
- `POST /api/agent/run`：运行 KnowledgeOps Agent 工作流
- `POST /api/eval/retrieval`：执行检索链路评估

## 后续升级方向

1. 将 SQLite 元数据存储升级为 PostgreSQL。
2. 接入 Qdrant/Milvus 作为向量数据库。
3. 接入 Elasticsearch/Meilisearch 或 PostgreSQL full-text 作为关键词索引。
4. 使用 bge-reranker、Jina Reranker 或 Cohere Rerank 替换启发式 rerank。
5. 使用 LangGraph 实现可观测、多步骤、可恢复的 Agent 工作流。
6. 引入 Celery/RQ + Redis，将文档解析、索引构建和运营报告改为异步任务。
7. 增加 RAGAS 或自定义 benchmark，评估召回率、引用覆盖率和答案忠实度。

