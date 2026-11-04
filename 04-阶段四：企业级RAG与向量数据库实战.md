# 阶段四：企业级 RAG 与向量数据库实战（第 6 ~ 7 周）

## 🎯 阶段学习目标
1. 深入理解 RAG（检索增强生成）在企业级 AI 应用中的核心价值与商业地位。
2. 掌握文档切分（Chunking）的艺术与参数调优（Chunk Size、Overlap）。
3. 掌握文本向量化（Embedding）与相似度匹配原理。
4. 掌握企业级最通用的向量存储方案：**PostgreSQL + pgvector**。
5. 掌握进阶技巧：**混合检索（Hybrid Search）与重排模型（Rerank）**，解决传统 RAG 搜不准的行业顽疾。

---

## 🔍 1. 为什么企业离不开 RAG？

大模型虽然博学，但存在三个硬伤：
1. **不知道企业内部私有数据**（如公司财务报销制度、内部代码规范、客户保密档案）；
2. **知识存在截止日期**（无法感知昨天刚更新的业务规则）；
3. **一本正经地胡说八道（幻觉）**。

**RAG（Retrieval-Augmented Generation）的解决之道**：
> “把闭卷考试变成开卷考试” —— 当用户提问时，先在企业本地文档库中搜索出最相关的段落，再把段落塞入 Prompt 告诉模型：“请根据以下参考资料回答用户问题，资料中没有提到的不要编造”。

```
用户提问 ──> [向量化 Embedding] ──> [检索向量库 Top-K 精准片段]
                                              │
                                              ▼
最终回答 <── [LLM 总结输出] <── [拼接参考资料 + 用户提问作为 Prompt]
```

---

## ✂️ 2. 文档分块（Chunking）与 Embedding 向量化

### 什么是 Chunking？
大模型上下文窗口有限且检索颗粒度需要精准，我们不能把一整本 200 页的 PDF 直接塞给模型。必须切分成小片段（例如每段 500 个字符）。

* **Chunk Size（分块大小）**：每块包含的字符数。太小（100字）缺乏上下文语义；太大（2000字）检索不聚焦。推荐起点：`400 ~ 600` 字符。
* **Chunk Overlap（重叠区域）**：相邻两块之间重叠的部分（通常设为 10%~20%，如 50 字符）。**目的**：防止一句话恰好在分块边缘被切断导致语义丢失。

### 什么是 Embedding？
通过 Embedding 模型（如 `text-embedding-3-small`），将任意一段自然语言转换成一串固定维度的浮点数数组（例如 1536 维向量）。
* **核心数学原理**：两个文本语义越接近，它们在多维空间中的**余弦相似度（Cosine Similarity）**越接近 1。

---

## 🗄️ 3. 为什么企业首选 PostgreSQL + pgvector？

很多初学者容易被各种独立的专用向量库（如 Milvus、Chroma、Pinecone）绕晕。  
但在真正的企业级生产环境中，**极其推崇在 PostgreSQL 中安装 `pgvector` 插件**：
* **单一数据源**：同一张表里既可以存业务数据（用户名、创建时间、订单号），又可以存向量字段。
* **事务与权限**：天然享受 PostgreSQL 成熟的 ACID 事务、行级权限控制和备份容灾方案，不需要维护两套数据库。

### SQL 实战快速演示
```sql
-- 1. 启用向量扩展插件
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建企业知识库文档分块表
CREATE TABLE knowledge_chunks (
    id SERIAL PRIMARY KEY,
    document_name VARCHAR(255),
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- 存储 1536 维度的向量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 基于余弦相似度进行快速 Top-3 检索查询
-- <=> 表示余弦距离计算符号
SELECT content, 1 - (embedding <=> '[0.012, -0.043, ...]') AS similarity
FROM knowledge_chunks
WHERE document_name = '2026员工差旅报销规范.pdf'
ORDER BY embedding <=> '[0.012, -0.043, ...]' ASC
LIMIT 3;
```

---

## 🏆 4. 解决“搜不准”的高级进阶秘籍

初级 RAG 经常被业务部门吐槽“搜不到”或“搜出来的东西答非所问”。企业级进阶方案必须掌握两张王牌：

1. **混合检索（Hybrid Search）**：
   * **向量检索**：擅长理解语义相似（比如搜“差旅住宿上限”，能命中“酒店开销预算”）；
   * **关键词检索（全文检索/BM25）**：擅长匹配专有名词、错误码、特定型号（比如搜“ERR_AUTH_9021”，向量检索经常模糊匹配，关键词检索百分百精准命中）；
   * 结合两者打分，召回率提升 40% 以上。
2. **重排（Rerank）**：
   * 初次检索可以粗召回 Top-20 条候选片段；
   * 通过专用的轻量重排模型（如 BGE-Reranker 或 Cohere Rerank）进行精细打分排序，筛选出最硬核的 Top-3 塞入 Prompt。

---

## 📋 阶段四实战作业

1. 注册体验 **Supabase**（免费提供自带 pgvector 的托管 PostgreSQL）或本地 Docker 启动一个带有 pgvector 的 PostgreSQL 容器。
2. 编写一段 Python 或 TypeScript 脚本：
   - 读取一份本地的 Markdown 或 TXT 文档；
   - 按照 500 字符切分，并调用 Embedding API 计算出向量；
   - 批量写入到数据库的向量表中。
3. 编写一个终端交互问答脚本：用户输入问题，系统自动去数据库检索出最相似的 3 个片段，拼装 Prompt 让大模型据此回答，并输出引用了哪一段资料。
