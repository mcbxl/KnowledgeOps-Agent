# 简历项目描述

## 项目名称

KnowledgeOps Agent：个人知识库运营与推理 Agent

## 一句话介绍

基于 RAG 与 LangGraph Agent 工作流构建个人知识库运营系统，支持多源知识接入、层级化切分、Hybrid Search、Rerank、引用溯源问答、知识冲突检测和主动治理报告，使用 MySQL 管理知识库元数据。

## 简历描述

设计并实现 KnowledgeOps Agent，一个面向个人/团队知识库的智能运营系统。系统支持 Markdown、网页、文件等多源知识接入，完成文档解析、自动摘要、标签生成、入库去重、层级化 chunking、embedding 向量化、Hybrid Search 检索、rerank 重排序和引用溯源问答。使用 MySQL 存储文档、chunk 和元数据，并基于 LangGraph StateGraph 编排 KnowledgeOps Agent 工作流，实现知识资产盘点、质量诊断、重复内容识别、冲突候选检测、FAQ 生成、学习路径规划和知识图谱构建，将知识库从被动问答工具升级为主动治理系统。

## 技术亮点

- 设计多源文档解析 Pipeline，支持 Markdown、网页和文件上传，自动提取标题、摘要、标签、来源和内容哈希。
- 使用 SQLAlchemy + MySQL 管理知识库元数据，并保留向量索引和关键词索引的可替换边界。
- 实现层级化 Chunking 策略，结合标题结构、段落语义边界和元数据继承，保留章节路径、来源和标签信息。
- 设计文档检查器，支持查看正文预览、内容哈希、chunk 列表、章节路径、Token 数和 embedding 维度，便于验证索引构建质量。
- 构建 Hybrid Search 检索链路，融合 BM25 风格关键词召回、Embedding 向量召回与 rerank 重排序，提高复杂问题召回准确率。
- 引入问题意图识别机制，根据事实、概念、总结、对比类问题动态调整关键词、向量和 rerank 权重。
- 实现引用溯源问答机制，将生成答案与原始文档片段绑定，返回文档名、章节路径、原文片段和相关度分数。
- 使用 LangGraph StateGraph 编排 Agent 节点，将资产盘点、质量诊断、冲突检测、检索探测和治理计划拆成可观测工作流。
- 实现证据化运营报告，为重复、低质量和冲突候选问题输出置信度、触发证据和建议治理动作。
- 设计 Topic Coverage 分析能力，识别薄弱主题、健康主题和高密度主题，为知识补全和学习路线生成提供依据。
- 自动生成 FAQ、学习路线和知识图谱数据，提升知识库的可维护性和复用价值。
- 提供检索评估服务，评估 TopK 召回、Top1 相关度和引用元数据完整性，为后续 RAG 质量评估打基础。

## 可继续扩展

- 接入 Qdrant 和 Elasticsearch/Meilisearch，实现生产级向量检索和关键词检索。
- 增加 Alembic migration 管理 MySQL 表结构演进。
- 接入 bge-reranker、Jina Reranker 或 Cohere Rerank，提高重排质量。
- 引入 RAGAS 或自定义 benchmark，评估检索召回率、引用覆盖率和答案忠实度。
