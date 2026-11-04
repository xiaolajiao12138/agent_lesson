"""
DAY 09 实战源码：RAG 核心体系 —— 文档分块、向量化与 Chroma 相似度检索
文件说明：
    当大模型缺乏企业私有业务数据时，RAG（检索增强生成）是最有效的落地技术。
    本文件演示轻量级开源向量数据库 Chroma 的核心使用闭环：
    文本输入 -> 结构化切分 -> 向量化 (Embedding) -> 余弦相似度召回。
运行要求：
    pip install chromadb openai
    python day09_vector_rag.py
"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# 1. 模拟企业内部知识库文档数据
# ---------------------------------------------------------------------------

KNOWLEDGE_DOCS = [
    {
        "id": "KB_001",
        "category": "人事规章",
        "text": "公司公休假规定：入职满一年的正式员工享受每年 5 天带薪年假。年假需提前 3 个工作日在内部 OA 提单申请。"
    },
    {
        "id": "KB_002",
        "category": "财务报销",
        "text": "差旅报销标准：出差到一类城市（北京、上海、深圳）住宿标准上限为 500 元/天，餐饮补贴 100 元/天，需提供增值税专用发票。"
    },
    {
        "id": "KB_003",
        "category": "安全合规",
        "text": "代码与数据安全规范：严禁将任何包含客户真实手机号、身份证、数据库生产连接密码的代码推送到公开仓库，违者严重警告直至解除合同。"
    },
    {
        "id": "KB_004",
        "category": "技术规范",
        "text": "前端工程规范：全员统一使用 TypeScript 5.0+ 进行开发，组件命名遵循 PascalCase，必须通过 ESLint 和 Prettier 严格校验方可合并分支。"
    }
]

# ---------------------------------------------------------------------------
# 2. 向量库客户端与集合 (Collection) 初始化
# ---------------------------------------------------------------------------

class SimpleVectorRAG:
    def __init__(self):
        # 初始化本地持久化或内存数据库实例
        # 类似前端 IndexedDB 的本地轻量存储
        self.chroma_client = chromadb.Client()
        
        # 使用内置的默认词嵌入转换模型（生产环境可切换为 OpenAI 的 text-embedding-3-small）
        self.embed_func = embedding_functions.DefaultEmbeddingFunction()
        
        # 创建一个向量集合（类似关系型数据库的一张表或 MongoDB 的一个 Collection）
        self.collection = self.chroma_client.get_or_create_collection(
            name="enterprise_knowledge_base",
            embedding_function=self.embed_func
        )
        self._index_documents()

    def _index_documents(self):
        """将文档向量化并写入索引"""
        print("正在将企业知识库文档灌入 Chroma 向量数据库...")
        
        ids = [doc["id"] for doc in KNOWLEDGE_DOCS]
        documents = [doc["text"] for doc in KNOWLEDGE_DOCS]
        metadatas = [{"category": doc["category"]} for doc in KNOWLEDGE_DOCS]

        # upsert: 存在则更新，不存在则插入
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"向量库构建完毕，共索引 {len(ids)} 篇文档。")

    def semantic_search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        语义相似度查询：
        将用户的提问实时计算为向量，并在高维空间寻找距离最近的 top_k 个文档。
        """
        print(f"\n用户提问语义检索: '{query}'")
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        matched_results = []
        for i in range(len(results["ids"][0])):
            doc_info = {
                "id": results["ids"][0][i],
                "category": results["metadatas"][0][i]["category"],
                "content": results["documents"][0][i],
                # 距离越小，相似度越高
                "distance": round(results["distances"][0][i], 4) if "distances" in results else None
            }
            matched_results.append(doc_info)

        return matched_results

# ---------------------------------------------------------------------------
# 测试检索效果
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rag = SimpleVectorRAG()

    # 测试一：没有出现完全匹配字眼，但具有极高语义关联的问题
    test_query_1 = "我去深圳出差一晚上住酒店花了480元，能全额报销吗？"
    hits = rag.semantic_search(test_query_1, top_k=1)
    for h in hits:
        print(f"命中切片 ID: {h['id']} | 分类: {h['category']} | 距离得分: {h['distance']}")
        print(f"切片详情: {h['content']}")

    # 测试二：技术开发规范检索
    test_query_2 = "写前端代码必须要用 TS 吗？"
    hits2 = rag.semantic_search(test_query_2, top_k=1)
    for h in hits2:
        print(f"\n命中切片 ID: {h['id']} | 分类: {h['category']} | 距离得分: {h['distance']}")
        print(f"切片详情: {h['content']}")
