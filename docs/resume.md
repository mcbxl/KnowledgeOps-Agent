# 简历项目描述

## 项目名称

KnowledgeOps Agent：个人知识库运营与推理 Agent

## 一句话介绍

基于 FastAPI、LangGraph、LangChain、MySQL 与 Qdrant 构建个人知识库运营 Agent，支持多源接入、真实 Embedding/LLM 接入、混合检索、引用溯源问答、质量诊断、冲突检测、检索评测与生产级安全校验。

## 简历描述

设计并实现 KnowledgeOps Agent，一个面向个人/团队知识库的智能运营系统。系统支持 Markdown、网页、文件上传等多源知识接入，完成文档解析、自动摘要、标签生成、入库去重、层级化 chunking、Embedding 向量化、Qdrant 向量索引、BM25 风格关键词召回、rerank 重排和引用溯源问答。使用 MySQL 管理文档、chunk、任务和元数据，通过 LangGraph StateGraph 编排 KnowledgeOps Agent 工作流，实现知识资产盘点、质量诊断、冲突候选检测、检索探测和治理计划生成，将知识库从被动问答工具升级为主动治理系统。

## 技术亮点

- 设计 Provider 化模型层，支持本地 deterministic embedding/answer generator 与 LangChain OpenAI Embeddings/ChatOpenAI 的生产切换，保证本地测试稳定、生产可接真实模型。
- 集成 Qdrant 向量数据库，文档入库时同步 upsert chunk 向量，查询时使用 Qdrant TopK 候选与 BM25、rerank 分数融合。
- 使用 LangGraph StateGraph 编排 Agent 节点，将资产盘点、质量诊断、冲突检测、检索探测和治理计划拆成可观测工作流。
- 构建引用溯源答案生成链路，LLM 仅基于召回上下文生成回答，并返回文档、章节路径、原文片段和相关度分数。
- 增加 Grounding Audit 能力，对答案与引用片段做 evidence coverage 检查，输出 groundedness 分数、unsupported terms 和风险提示。
- 实现层级化 Chunking 策略，结合标题结构、段落语义边界和元数据继承，保留章节路径、来源和标签信息。
- 使用 SQLAlchemy + MySQL 管理知识库元数据，同时保留 SQLite 注入能力，支持无 MySQL 环境下的自动化测试。
- 增加生产安全边界：API Key 鉴权、请求追踪 ID、URL 接入拦截 localhost/private IP 等 SSRF 风险目标，上传限制文件大小和扩展名，CORS 来源通过环境变量配置。
- 实现 Runtime Readiness 自检接口和前端面板，展示数据库、Embedding、LLM、Qdrant 和安全策略的生产就绪状态。
- 提供检索评测服务，评估 TopK 召回、Top1 分数和 citation-ready 比例，为后续 RAGAS/自定义 benchmark 打基础。
- 为运维任务中心设计任务表，记录任务状态、输入参数、执行结果和错误信息，便于后续替换为 Celery/RQ + Redis。

## 可演示能力

- 导入一篇 Markdown 或网页文档，查看生成的 chunks、章节路径、token 数和 embedding 维度。
- 在 `/api/search` 中观察 lexical/vector/rerank 三类分数，展示 Hybrid Search 可解释性。
- 在 `/api/ask` 中展示 LLM 或本地 generator 的引用溯源回答和 Grounding Audit。
- 在 `/api/agent/run` 中运行 LangGraph Agent，查看每个治理阶段的 observation、evidence 和 next actions。
- 在 `/api/runtime/status` 中展示真实模型、Qdrant、数据库和安全配置的 runtime readiness。
- 在 `/api/eval/retrieval` 中执行检索评测，展示测试覆盖和质量评估意识。
