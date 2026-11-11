"""
DAY 11 实战源码：生产级 RAG 效果优化 —— 来源引用溯源与防幻觉控制
==============================================================================
【文件导读】：
    如果 RAG 系统只是粗暴地把向量库检索到的文本片段塞进提示词，
    大模型很容易出现“看似有理有据，实则胡编乱造”的幻觉，或者把模型训练预料里的无依据常识混杂进来。

    企业级 RAG 的两大核心标配：
    1. 强制引用溯源 (Citations / Grounding)：
       大模型在陈述每一条事实时，必须在句末标明引用的切片 ID（如 [KB_001]），方便前端高亮溯源原文。
    2. 防幻觉 Prompt 栅栏 (Guardrails)：
       如果知识库未提及，必须明确拒答，严禁脑补发散。
    3. Temperature = 0.0：
       将采样温度压到最低，关闭随机性，强制模型只依据客观证据贪婪采样。

【运行要求】：
    pip install chromadb openai python-dotenv
    python day11_advanced_rag_rerank.py
==============================================================================
"""

import os
<<<<<<< HEAD
import sys

from dotenv import load_dotenv

# 确保当前目录和父目录均可正常导包
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 1. 优先加载本地或根目录的 .env 文件
load_dotenv(os.path.join(parent_dir, ".env"), override=True)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

# 2. 直接在当前页面设置 OpenAI Key、Base URL 与 Model
# （优先读取 .env；若未配置则直接使用下面当前页面写好的 Key）
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

# 3. 注入系统环境变量（供 OpenAI 官方 SDK 自动读取）
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL
os.environ["OPENAI_API_BASE"] = OPENAI_BASE_URL
=======
>>>>>>> 9527dd1d52ec943c35a53668ceacecce547d3cfb

from day09_vector_rag import SimpleVectorRAG

# ==============================================================================
# 生产级带来源引用的 RAG 问答引擎
# ==============================================================================


class ProductionCitationRAG:
    """生产级带来源引用的 RAG 问答系统实现"""

    def __init__(self):
        # 1. 挂载上节课封装的向量检索库
        self.vector_store = SimpleVectorRAG()

    def generate_grounded_answer(self, user_question: str) -> str:
        """
        【全流程标准流水线】：
        1. 检索阶段：召回与问题语义最相关的 Top-K 知识切片；
        2. 组装阶段：构建带有明确文档 ID 标签的结构化参考上下文；
        3. 约束阶段：注入带有防幻觉铁律的 System Prompt；
        4. 推理阶段：以 temperature=0.0 请求大模型输出带溯源角标的回答。
        """
        from openai import OpenAI

        # 初始化客户端（传入显式配置好的 Key 和中转地址）
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )

        # 步骤 1：向量相似度召回最相关的 2 篇文档
        retrieved_chunks = self.vector_store.semantic_search(user_question, top_k=2)

        if not retrieved_chunks:
            return "知识库中暂未收录相关信息。"

        # 步骤 2：拼接带编号与分类的结构化上下文（方便大模型明确识别）
        context_parts = []
        for chunk in retrieved_chunks:
            part = f"【参考文档 ID: {chunk['id']} | 分类: {chunk['category']}】\n{chunk['content']}"
            context_parts.append(part)
        formatted_context = "\n\n".join(context_parts)

        # 步骤 3：设计极其严谨的防幻觉三铁律 System Prompt
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

        print("\n--- 正在调用大模型生成带溯源引用的答案 (Temperature=0.0) ---")

        # 步骤 4：请求 LLM
        response = client.chat.completions.create(
<<<<<<< HEAD
            model=DEFAULT_MODEL,
=======
            model="gpt-4o",
>>>>>>> 9527dd1d52ec943c35a53668ceacecce547d3cfb
            temperature=0.0,  # 严谨问答场景下务必将温度设为 0，杜绝幻觉
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_payload},
            ],
        )

        return response.choices[0].message.content


# ==============================================================================
# 本地测试与防幻觉验证
# ==============================================================================

if __name__ == "__main__":
    import time

    q1 = "请问刚入职半年的员工可以申请休几天年假？"
    q2 = "请问公司下午茶提供星巴克咖啡吗？"

<<<<<<< HEAD
    try:
        start_time = time.time()
        rag_engine = ProductionCitationRAG()

        print(f"\n[问题 1]: {q1}")
        ans1 = rag_engine.generate_grounded_answer(q1)
        print(f"[回答 1]:\n{ans1}")

        print(f"\n[问题 2]: {q2}")
        ans2 = rag_engine.generate_grounded_answer(q2)
        print(f"[回答 2]:\n{ans2}")
        end_time = time.time()
        print(f"\n[总耗时]: {end_time - start_time:.2f} 秒")
    except Exception as e:
        print(f"[调用异常]: {e}")
=======
    if not os.getenv("OPENAI_API_KEY"):
        print("\n" + "=" * 60)
        print("[提示] 检测到当前系统未设置 OPENAI_API_KEY 环境变量。")
        print("以下展示大模型在严格防幻觉规则约束下的真实预期响应演示：")
        print("=" * 60)

        print(f"\n[问题 1 测试]：{q1}")
        print(
            "[知识库检索到的切片]：KB_001 (入职满一年的正式员工享受每年 5 天带薪年假...)"
        )
        print("[模型带溯源的严谨回答]：")
        print(
            "根据公司规定，入职满一年的正式员工才享受每年 5 天带薪年假，因此刚入职半年的员工暂不支持享受带薪年假 [KB_001]。"
        )

        print("-" * 60)
        print(f"\n[问题 2 测试（知识库中没有的内容）]：{q2}")
        print(
            "[知识库检索结果]：未召回相关切片（仅召回人事/差旅/代码规范等不相关内容）"
        )
        print("[模型严谨拒答，拒绝脑补]：")
        print("依据现有制度文档，未找到关于公司下午茶是否提供星巴克咖啡的明确规定。")
        print("=" * 60 + "\n")
    else:
        try:
            rag_engine = ProductionCitationRAG()

            print(f"\n[问题 1]: {q1}")
            ans1 = rag_engine.generate_grounded_answer(q1)
            print(f"[回答 1]:\n{ans1}")

            print(f"\n[问题 2]: {q2}")
            ans2 = rag_engine.generate_grounded_answer(q2)
            print(f"[回答 2]:\n{ans2}")
        except Exception as e:
            print(f"[调用异常]: {e}")
>>>>>>> 9527dd1d52ec943c35a53668ceacecce547d3cfb
