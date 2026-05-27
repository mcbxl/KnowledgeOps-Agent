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
  └─ 知识图谱

后端服务
  ├─ Document Ingestion Service
  ├─ Chunking & Metadata Pipeline
  ├─ Embedding Service
  ├─ Hybrid Retrieval Service
  ├─ Answer Agent
  ├─ KnowledgeOps Agent
  └─ Retrieval Evaluation Service

存储层
  ├─ SQLite：本地开发版本的文档、chunk、元数据
  ├─ PostgreSQL：生产版本的元数据存储升级方向
  ├─ Qdrant/Milvus：生产版本向量索引升级方向
  └─ Elasticsearch/Meilisearch：生产版本关键词索引升级方向
```

## 文档接入流程

1. 用户导入 Markdown、文本、网页或文件。
2. 系统提取标题、正文、来源、标签、摘要和内容哈希。
3. 通过内容哈希进行入库去重。
4. Chunking Pipeline 按标题层级和段落语义边界切分。
5. 每个 chunk 绑定文档 ID、章节路径、顺序、标签和 embedding。
6. chunk 和文档元数据写入本地存储。

## 分块策略

当前实现不是简单固定长度切分，而是结合：

- Markdown 标题层级
- 段落边界
- 语义长度窗口
- 章节路径保留
- 标签继承
- 来源与顺序元数据

这样做的好处是回答时可以展示“来自哪篇文档、哪个章节、哪段原文”，避免 RAG 系统常见的引用不可追踪问题。

## Hybrid Search 检索链路

检索分为三类分数：

1. **关键词分数**：BM25 风格，用于精确实体、API 名称、版本号、错误码等。
2. **向量分数**：本地确定性 embedding，用于语义相似和概念类问题。
3. **Rerank 分数**：结合 query-token 覆盖、章节标题命中和 chunk 长度进行重排。

系统会先识别问题意图：

- 事实类：提高关键词权重
- 概念类：提高向量权重
- 总结类：扩大语义召回权重
- 对比类：平衡多来源召回

## 引用溯源问答

问答模块只基于检索到的知识库片段生成答案，并返回：

- 文档 ID
- chunk ID
- 文档标题
- 章节路径
- 原文片段
- 相关度分数

这使回答结果具备可验证性，面试时可以强调“答案不是凭空生成，而是绑定原始证据”。

## KnowledgeOps Agent 工作流

`KnowledgeOpsAgent` 当前实现为本地规则编排，后续可以平滑升级为 LangGraph。工作流阶段包括：

1. **资产盘点**：统计文档数量、chunk 数量、整体质量分。
2. **质量诊断**：识别低质量文档，如过短、缺少结构化标题、信息密度不足。
3. **冲突检测**：识别版本迁移、废弃 API、互斥结论等冲突候选。
4. **检索探测**：用主题词对检索链路进行快速健康检查。
5. **治理计划**：生成下一步运营动作和 backlog。

每个诊断问题都包含：

- `kind`：问题类型，如重复、低质量、冲突候选。
- `severity`：严重程度。
- `confidence`：启发式置信度。
- `evidence`：触发判断的证据，如 chunk 片段、分数、冲突词对。
- `suggested_actions`：建议采取的治理动作。

这使 Agent 的输出具备可解释性，避免只有结论没有依据。

## 冲突检测设计

当前版本实现启发式冲突候选检测，重点识别：

- deprecated/recommended 表述冲突
- 旧 API 和新 API 并存
- should/should not 等互斥表达
- “旧/新”“必须/不要”等中文冲突线索

高级版本可升级为：

1. 实体和主题聚类
2. 声明性事实抽取
3. NLI 或 LLM 一致性判断
4. 冲突置信度评分
5. 人工确认和权威版本标记

## 检索评估设计

`RetrievalEvaluationService` 用固定 query 评估：

- TopK 召回数量
- Top1 相关度
- 引用元数据是否完整
- 是否需要优化标题、标签、分块或索引

后续可以扩展为标准 benchmark：记录 query、期望命中文档、期望 chunk、答案忠实度和引用覆盖率。

## Topic Coverage 设计

Topic Coverage 用文档标签和 chunk 标签统计主题覆盖：

- `thin`：主题内容过薄，可能只有少量文档或 chunk。
- `healthy`：主题覆盖适中，适合生成 FAQ 或学习路线。
- `dense`：主题内容密集，适合做专题总结、对比分析或知识图谱扩展。

该能力可用于发现知识库中的薄弱主题和待补充知识点。

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
