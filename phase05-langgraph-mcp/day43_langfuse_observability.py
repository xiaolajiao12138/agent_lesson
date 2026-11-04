"""
DAY 43 实战源码：Agent 链路追踪与生产可观测性（基于 Langfuse）
文件说明：
    智能体上线后，如果用户抱怨“回答太慢”或“回答不准”，或者老板问“这个月大模型 API 花了多少钱”，
    没有可观测性平台你将两眼一抹黑。
    本文件演示如何通过开源可观测性平台 Langfuse 实现：
    1. 每一轮 Agent 推理的 Trace / Span 瀑布流追踪；
    2. Token 消耗统计与成本实时核算；
    3. 自定义用户评分与反馈回流。
运行要求：
    pip install langfuse openai
    python day43_langfuse_observability.py
"""

import os
from openai import OpenAI
from langfuse.openai import OpenAI as TracedOpenAI
from langfuse import Langfuse

# ---------------------------------------------------------------------------
# 1. 配置 Langfuse 凭据（可使用官方云服务或自己 Docker 私有化部署）
# ---------------------------------------------------------------------------
# os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
# os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
# os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"

class AgentObservabilityDemo:
    def __init__(self):
        # TracedOpenAI 是对官方 OpenAI 客户端的完全透明包装
        # 只要用它发起的所有请求，都会自动在后台异步上报完整的调用链
        self.traced_client = TracedOpenAI()
        self.langfuse = Langfuse()

    def run_monitored_workflow(self, user_id: str, query: str):
        """
        发起一次被全方位监控的 Agent 推理调用
        """
        print(f"\n[APM 监控中] 收到终端用户 [{user_id}] 提问: {query}")
        
        # 发起调用，并在额外参数中注入业务上下文标签
        response = self.traced_client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是一名精通现代 Web 架构与 Agent 的技术专家。"},
                {"role": "user", "content": query}
            ],
            # 专属追踪元数据（可在 Langfuse 控制台按照标签、用户和环境进行多维筛选）
            name="agent-architecture-consulting",
            user_id=user_id,
            tags=["production", "frontend-transform", "q3-demo"],
            metadata={
                "client_framework": "Next.js 15",
                "request_origin": "Shanghai, China"
            }
        )

        answer = response.choices[0].message.content
        
        # 打印使用量统计（SDK 已经自动为你上报到了 Langfuse 云端）
        usage = response.usage
        print("✅ 任务执行成功！监控数据已自动上报:")
        print(f"   输入 Prompt Tokens: {usage.prompt_tokens}")
        print(f"   输出 Completion Tokens: {usage.completion_tokens}")
        print(f"   本次调用总计 Tokens: {usage.total_tokens}")
        
        return answer

if __name__ == "__main__":
    print("=== Langfuse Agent 链路追踪演示 ===")
    demo = AgentObservabilityDemo()
    
    test_user = "usr_frontend_dev_1001"
    test_query = "请用 3 句话总结前端开发者转型 AI Agent 的最大核心竞争优势。"
    
    try:
        result = demo.run_monitored_workflow(test_user, test_query)
        print(f"\n模型生成内容:\n{result}")
        print("\n提示：如已配置环境变量，请登录 Langfuse 控制台查看详细瀑布流 Trace 图表与 Token 计费！")
    except Exception as e:
        print(f"执行异常（未配置密钥或网络原因）: {e}")
