import os
import time

OPENAI_API_KEY = (
    os.getenv("api_key")
    or os.getenv("OPENAI_API_KEY")
    or "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"
)
OPENAI_BASE_URL = (
    os.getenv("base_url")
    or os.getenv("OPENAI_BASE_URL")
    or "https://sub2api.starysp.top/v1"
)
DEFAULT_MODEL = os.getenv("mode") or "gpt-6.1-sol"

from day09_vector_rag import SimpleVectorRAG


class testRag:
    def __init__(self):
        self.vector_store = SimpleVectorRAG()

    def answer_search(self, query, top_k=2) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
        retrieved_docs = self.vector_store.semantic_search(query, top_k=top_k)
        if not retrieved_docs:
            return "未找到相关文档"
        content = []
        for doc in retrieved_docs:
            part = f"【参考文档ID：{doc['id']} | 分类：{doc['category']}】\n{doc['content']}"
            content.append(part)
        format_content = "\n\n".join(content)
        # 步骤 3：设计极其严谨的防幻觉三铁律 System Prompt
        system_prompt = (
            "你是一个企业内部严谨的知识库检索助手。\n"
            "你必须严格遵循以下三项铁律：\n"
            "1. 你的回答必须 100% 来源于给定的【参考文档】，绝对不允许添加文档中没有提及的个人推测或常识补全；\n"
            "2. 如果【参考文档】中的内容不足以完全回答用户的问题，必须明确告知用户：'依据现有制度文档，未找到关于该问题的明确规定'；\n"
            "3. 凡是引用了文档内容的关键事实陈述，必须在句末标注对应的文档 ID，格式必须形如：[KB_002]。"
        )
        user_payload = (
            f"【用户问题】：{query}\n\n"
            f"【参考文档】：\n{format_content}"
            f"请按照要求开始严谨作答"
        )
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.0,  # 严谨问答场景下必须将温度设为0，杜绝幻觉
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    q1 = "请问刚入职半年的员工可以申请休几天年假？"
    q2 = "请问公司下午茶提供星巴克咖啡吗？"
    start_time = time.time()
    rag = testRag()
    ans1 = rag.answer_search(q1, top_k=2)
    ans2 = rag.answer_search(q2, top_k=2)
    end_time = time.time() - start_time

    print(f"[问题 1]: {q1}")
    print(f"[回答 1]:\n{ans1}")
    print(f"\n[问题 2]: {q2}")
    print(f"[回答 2]:\n{ans2}")
    print(f"\n[总耗时]: {end_time:.2f} 秒")
