"""
DAY 11 实战源码：生产级 RAG 效果优化 —— 来源引用溯源与防幻觉控制
文件说明：
    如果 RAG 只是把检索到的片段塞给模型，模型很容易胡编乱造或者把无关信息掺杂进来。
    企业级 RAG 的两大标配：
    1. 强制引用溯源 (Citations)：模型在陈述事实时必须标明引用了哪个文档切片 ID。
    2. 防幻觉 Prompt 栅栏 (Guardrails)：文档没提到的直接答不知，严禁自作聪明。
运行要求：
    pip install chromadb openai
    python day11_advanced_rag_rerank.py
"""

import json
from openai import OpenAI
from day09_vector_rag import SimpleVectorRAG

class ProductionCitationRAG:
    """生产级带来源引用的 RAG 问答系统"""

    def __init__(self):
        # 复用上节课封装好的向量知识库
        self.vector_store = SimpleVectorRAG()
        self.llm_client = OpenAI() # 自动获取 OPENAI_API_KEY

    def generate_grounded_answer(self, user_question: str) -> str:
        """
        全流程处理：
        1. 检索 Top-K 知识切片
        2. 格式化构建结构化上下文（带有 [Doc ID] 标识）
        3. 发送给经过严格系统提示词约束的 LLM
        """
        # 1. 语义召回最相关的 2 篇文档
        retrieved_chunks = self.vector_store.semantic_search(user_question, top_k=2)

        if not retrieved_chunks:
            return "知识库中暂未收录相关信息。"

        # 2. 拼接结构化上下文
        context_parts = []
        for chunk in retrieved_chunks:
            part = f"【参考文档 ID: {chunk['id']} | 分类: {chunk['category']}】\n{chunk['content']}"
            context_parts.append(part)
        formatted_context = "\n\n".join(context_parts)

        # 3. 严格的系统人设与防幻觉指令
        system_prompt = (
            "你是一个企业内部严谨的知识库检索助手。\n"
            "你必须严格遵循以下三项铁律：\n"
            "1. 你的回答必须 100% 来源于给定的【参考文档】，绝对不允许添加文档中没有提及的个人推测或常识补全；\n"
            "2. 如果【参考文档】中的内容不足以完全回答用户的问题，必须明确告知用户：'依据现有制度文档，未找到关于该问题的明确规定'；\n"
            "3. 凡是引用了文档内容的关键事实陈述，必须在句末标注对应的文档 ID，格式必须形如：[KB_002]。"
        )

        user_prompt_payload = (
            f"【参考文档清单】：\n{formatted_context}\n\n"
            f"【员工提问】：{user_question}\n\n"
            f"请按照要求开始严谨作答："
        )

        print("\n--- 正在调用大模型生成带溯源引用的答案 ---")
        response = self.llm_client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0, # 严谨问答务必将温度设为 0
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_payload}
            ]
        )

        return response.choices[0].message.content

if __name__ == "__main__":
    rag_engine = ProductionCitationRAG()

    # 提问一：知识库中有明确支持的问题
    q1 = "请问刚入职半年的员工可以申请休几天年假？"
    try:
        ans1 = rag_engine.generate_grounded_answer(q1)
        print(f"\n[回答一]:\n{ans1}")
    except Exception as e:
        print(f"调用异常（请配置合法 API Key）: {e}")

    # 提问二：知识库中根本没有的事项（测试防幻觉与拒答机制）
    q2 = "请问公司下午茶提供星巴克咖啡吗？"
    try:
        ans2 = rag_engine.generate_grounded_answer(q2)
        print(f"\n[回答二]:\n{ans2}")
    except Exception as e:
        print(f"调用异常: {e}")
