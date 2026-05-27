# 系统架构设计

## 项目定位

KnowledgeOps Agent 面向个人或团队知识库，核心目标不是简单 RAG 问答，而是持续运营知识资产。系统通过文档接入、结构化切分、混合检索、引用问答、冲突检测和治理建议，让知识库具备“自我诊断”和“主动维护”的能力。

## 总体架构

```text
前端工作台
  ├─ 文档导入
  ├─ 知识库检索
  ├─ 引用问答
  ├─ 运营报告
  ├─ Agent 工作流
  ├─ 检索评估
  └─ 知识图谱

后端服务
  ├─ Document Ingestion Service
  ├─ Chunking & Metadata Pipeline
  ├─ Embedding Service
  ├─ Hybrid Retrieval Service
  ├─ Answer Agent
  ├─ LangGraph KnowledgeOps Agent
  └─ Retrieval Evaluation Service

存储层
  ├─ MySQL：文档、chunk、标签、摘要、引用、报告元数据
  ├─ Qdrant/Milvus：向量索引升级方向
  └─ Elasticsearch/Meilisearch：关键词索引升级方向
```

## MySQL 存储设计

后端通过 SQLAlchemy 访问 MySQL。核心表包括：

- `documents`：文档标题、正文、来源类型、来源 URI、标签、摘要、内容哈希、创建时间。
- `chunks`：chunk 正文、章节路径、顺序、页码、标签、embedding JSON。

本地测试仍可注入 SQLite URL，以保证没有 MySQL 服务时也能跑单元测试；生产运行默认使用 `KNOWLEDGEOPS_DATABASE_URL` 指向 MySQL。

## 文档接入流程

1. 用户导入 Markdown、文本、网页或文件。
2. 系统提取标题、正文、来源、标签、摘要和内容哈希。
3. 通过内容哈希进行入库去重。
4. Chunking Pipeline 按标题层级和段落语义边界切分。
5. 每个 chunk 绑定文档 ID、章节路径、顺序、标签和 embedding。
6. chunk 和文档元数据写入 MySQL。

## Hybrid Search 检索链路

检索分为三类分数：

1. **关键词分数**：BM25 风格，用于精确实体、API 名称、版本号、错误码等。
2. **向量分数**：本地确定性 embedding，用于语义相似和概念类问题。
3. **Rerank 分数**：结合 query-token 覆盖、章节标题命中和 chunk 长度进行重排。

系统会识别问题意图：

- 事实类：提高关键词权重
- 概念类：提高向量权重
- 总结类：扩大语义召回权重
- 对比类：平衡多来源召回

## LangGraph Agent 工作流

`KnowledgeOpsAgent` 使用 LangGraph `StateGraph` 编排，每个阶段是一个 graph node，共享 `AgentState`，通过 `compile().invoke()` 执行。

工作流阶段包括：

1. **Asset inventory**：统计文档数量、chunk 数量、整体质量分。
2. **Quality diagnosis**：识别低质量文档，如过短、缺少结构化标题、信息密度不足。
3. **Conflict detection**：识别版本迁移、废弃 API、互斥结论等冲突候选。
4. **Retrieval probe**：用主题词对检索链路进行快速健康检查。
5. **Governance plan**：生成下一步运营动作和 backlog。

每个诊断问题都包含：

- `kind`：问题类型，如重复、低质量、冲突候选。
- `severity`：严重程度。
- `confidence`：启发式置信度。
- `evidence`：触发判断的证据。
- `suggested_actions`：建议采取的治理动作。

## Topic Coverage 设计

Topic Coverage 用文档标签和 chunk 标签统计主题覆盖：

- `thin`：主题内容过薄，可能只有少量文档或 chunk。
- `healthy`：主题覆盖适中，适合生成 FAQ 或学习路线。
- `dense`：主题内容密集，适合做专题总结、对比分析或知识图谱扩展。

## 知识图谱设计

当前图谱包含三类节点：

- `document`：知识来源文档。
- `section`：文档中的章节节点。
- `topic`：由标签和关键词生成的主题节点。

边类型包括：

- `tagged_as`：文档属于某个主题。
- `has_section`：文档包含某个章节。
- `mentions`：章节提到某个主题。

生产版本可以继续加入实体节点、概念节点、引用关系和冲突关系。

