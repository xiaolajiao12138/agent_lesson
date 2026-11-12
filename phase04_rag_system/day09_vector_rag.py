"""
DAY 09 实战源码：RAG 核心体系 —— 文档分块、向量化与 Chroma 相似度检索
==============================================================================
【文件导读】：
    当大模型缺乏企业私有业务数据、最新时效资讯或领域内幕资料时，
    RAG（Retrieval-Augmented Generation 检索增强生成）是最有效的落地技术。

    本文件演示轻量级开源向量数据库 Chroma 的核心使用闭环：
    知识录入 -> 结构化打标 -> 向量嵌入 (Embedding) -> 高维空间余弦/欧氏距离相似度召回。

【核心概念透析】：
    1. 为什么不能只用传统数据库做模糊搜索（LIKE '%xxx%'）？
       - 传统搜索必须字面匹配：例如用户搜“去深圳住酒店报销”，如果原文写的是“一类城市住宿标准”，
         传统 SQL LIKE 搜索直接 0 命中！
       - 向量搜索（Embedding）：将每句话映射为一串 1536 维的高维浮点数坐标。
         在空间中，“住酒店”与“住宿标准”的坐标距离极近，哪怕字面完全不同，也能精准命中！

    2. Chroma 向量数据库架构对标：
       - Chroma Client <---> 类似 MongoDB / Redis 连接实例
       - Collection    <---> 类似关系型数据库的一张表或 MongoDB Collection
       - Embedding     <---> 将文字转化为高维坐标的数学算法

【运行要求】：
    pip install chromadb
    python day09_vector_rag.py
==============================================================================
"""

import json

# ==============================================================================
# 1. 模拟企业内部知识库文档数据 (Knowledge Chunks)
# ==============================================================================
# 在实际工程中，这些文本往往是从 PDF、Markdown、Word 或 Notion 提取并切块后的知识切片 (Chunks)
KNOWLEDGE_DOCS = [
    {
        "id": "KB_001",
        "category": "人事规章",
        "text": "公司公休假规定：入职满一年的正式员工享受每年 5 天带薪年假。年假需提前 3 个工作日在内部 OA 提单申请。",
    },
    {
        "id": "KB_002",
        "category": "财务报销",
        "text": "差旅报销标准：出差到一类城市（北京、上海、深圳）住宿标准上限为 500 元/天，餐饮补贴 100 元/天，需提供增值税专用发票。",
    },
    {
        "id": "KB_003",
        "category": "安全合规",
        "text": "代码与数据安全规范：严禁将任何包含客户真实手机号、身份证、数据库生产连接密码的代码推送到公开仓库，违者严重警告直至解除合同。",
    },
    {
        "id": "KB_004",
        "category": "技术规范",
        "text": "前端工程规范：全员统一使用 TypeScript 5.0+ 进行开发，组件命名遵循 PascalCase，必须通过 ESLint 和 Prettier 严格校验方可合并分支。",
    },
]

# ==============================================================================
# 2. 向量库客户端与集合 (Collection) 初始化
# ==============================================================================


class SimpleVectorRAG:
    """
    轻量级向量检索系统实现
    """

    def __init__(self):
        import chromadb
        from chromadb.utils import embedding_functions

        # 1. 初始化 Chroma 内存客户端（开发调试首选，不产生本地垃圾文件；生产环境可用 PersistentClient 存盘）
        self.chroma_client = chromadb.Client()

        # 2. 选择文本向量化嵌入算法（此处使用 Chroma 内置的默认算法，也可切换为 OpenAI text-embedding-3-small）
        self.embed_func = embedding_functions.DefaultEmbeddingFunction()

        # 3. 创建或获取一个向量集合（相当于一张存放知识向量的数据表）
        self.collection = self.chroma_client.get_or_create_collection(
            name="enterprise_knowledge_base", embedding_function=self.embed_func
        )
        print("初始化")
        # 初始化时自动完成建库建索引
        self._index_documents()

    def _index_documents(self):
        """
        【文档灌库与构建向量索引】
        将普通纯文本转为多维数学向量，并存入底层 HNSW 向量索引图中。
        """
        print("[1/2] 正在将企业知识库文档切片灌入 Chroma 向量数据库...")

        ids = [doc["id"] for doc in KNOWLEDGE_DOCS]
        documents = [doc["text"] for doc in KNOWLEDGE_DOCS]
        metadatas = [{"category": doc["category"]} for doc in KNOWLEDGE_DOCS]

        # upsert: 存在则按 ID 更新，不存在则直接追加插入
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        print(f"[2/2] 向量索引库构建完毕，共成功索引 {len(ids)} 篇知识文档。")

    def semantic_search(self, query: str, top_k: int = 2) -> list[dict[str, any]]:
        """
        【高维语义相似度查询】
        参数：
          query: 用户的自然语言提问（比如 '去深圳住酒店报销'）
          top_k: 最多召回几条最相关的知识切片
        返回：
          按相关度从高到低排序的知识切片列表
        """
        print(f"\n[执行语义检索] 用户输入: '{query}'")

        # Chroma 底层会自动把 query 转换成同一个维度的向量，然后在高维空间计算距离
        results = self.collection.query(query_texts=[query], n_results=top_k)
        print(f"[检索结果] 共命中 {len(results['ids'][0])} 条相关知识切片。")
        matched_results = []
        for i in range(len(results["ids"][0])):
            doc_info = {
                "id": results["ids"][0][i],
                "category": results["metadatas"][0][i]["category"],
                "content": results["documents"][0][i],
                # 距离得分（Distance）：在欧氏距离度量下，数值越小代表两者在高维空间越挨得近，相似度越高
                "distance": round(results["distances"][0][i], 4)
                if "distances" in results
                else None,
            }
            matched_results.append(doc_info)

        return matched_results


# ==============================================================================
# 3. 测试检索效果验证
# ==============================================================================

if __name__ == "__main__":
    try:
        rag = SimpleVectorRAG()

        # ----------------------------------------------------------------------
        # 测试一：语义泛化测试
        # 问题中完全没有出现“一类城市”这四个字，但向量检索能识别“深圳”、“住酒店”、“报销”
        # ----------------------------------------------------------------------
        test_query_1 = "我去深圳出差一晚上住酒店花了480元，能全额报销吗？"
        hits = rag.semantic_search(test_query_1, top_k=1)
        print(json.dumps(hits))
        for h in hits:
            print(
                f"-> 命中切片 ID: {h['id']} | 所属分类: {h['category']} | 空间距离: {h['distance']}"
            )
            print(f"-> 切片正文: {h['content']}")

        # ----------------------------------------------------------------------
        # 测试二：技术规范语义匹配测试
        # # ----------------------------------------------------------------------
        # test_query_2 = "写前端代码必须要用 TS 吗？"
        # hits2 = rag.semantic_search(test_query_2, top_k=1)
        # for h in hits2:
        #     print(f"\n-> 命中切片 ID: {h['id']} | 所属分类: {h['category']} | 空间距离: {h['distance']}")
        #     print(f"-> 切片正文: {h['content']}")

        # print("\n" + "=" * 60)
        # print("[总结] 向量数据库成功根据语义相关度完成了知识召回！")
        # print("在实际 Agent 中，这些召回的切片正文会被拼装进 Prompt 作为参考背景输入大模型。")
        # print("=" * 60)

    except ImportError:
        print(
            "[提示] 本地未安装 chromadb 依赖，可执行: pip install chromadb 进行安装体验。"
        )
