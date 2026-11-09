"""
DAY 43 实战源码：Agent 链路追踪与生产可观测性（基于 Langfuse）
==============================================================================
【文件导读】：
    当智能体服务上线到生产环境后，你必然会面对三大灵魂拷问：
    1. 性能问题：用户反馈“今天 AI 回复怎么要 15 秒？究竟卡在网络搜索、知识库检索还是模型推理？”
    2. 成本问题：财务问“上个月大模型 API 账单花了 3 万块，到底是哪个大客户或哪个接口消耗的？”
    3. 质量问题：用户点了一个“差评（踩）”，你如何复现并定位当时究竟是哪一步出了 bug？

    Langfuse 是目前大模型与 Agent 领域最主流的开源可观测性（APM）平台：
    - Trace 树状调用链路（类似前端 Chrome DevTools Network 瀑布流，一眼看出每个步骤的耗时）；
    - 自动统计每位用户的 Prompt/Completion Token 与真实花费账单；
    - 用户反馈（赞/踩/评分）与具体 Trace 自动关联，形成评估飞轮。

【运行要求】：
    pip install langfuse openai
    python day43_langfuse_observability.py
==============================================================================
"""

import os
from typing import Dict, Any

# ==============================================================================
# 生产级链路追踪客户端封装
# ==============================================================================

class AgentObservabilityDemo:
    """
    智能体生产级全链路监控示例
    """

    def __init__(self):
        # 提示：实际生产中需要配置这三项环境变量：
        # os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
        # os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
        # os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com" (或私有部署地址)
        pass

    def run_monitored_workflow(self, user_id: str, query: str):
        """
        发起一次被全链路打标、监控与计费的 Agent 推理调用
        """
        from langfuse.openai import OpenAI as TracedOpenAI
        
        # TracedOpenAI 是官方 SDK 提供的透明代理包装：
        # 只要用它发起请求，底层会在后台异步且无侵入地收集延迟、Token 和 Trace 上报云端
        traced_client = TracedOpenAI()

        print(f"\n[APM 监控中] 收到终端用户 [{user_id}] 提问: {query}")
        
        # 发起调用，并在额外参数中注入丰富的业务上下文标签
        response = traced_client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是一名精通现代 Web 架构与 Agent 的技术专家。"},
                {"role": "user", "content": query}
            ],
            # 【核心追踪元数据】：这些字段都会原样落库到 Langfuse 的分析面板中
            name="agent-architecture-consulting", # 本次 Trace 追踪名称
            user_id=user_id,                      # 终端用户 ID（可用于统计高频重度用户）
            tags=["production", "frontend-transform", "q3-demo"], # 业务标签，方便在后台进行多维过滤
            metadata={
                "client_framework": "Next.js 15",
                "request_origin": "Shanghai, China",
                "environment": "production"
            }
        )

        answer = response.choices[0].message.content
        
        # 打印使用量统计（SDK 已经自动为你上报到了 Langfuse 云端）
        usage = response.usage
        print("\n[监控埋点已成功上报云端]:")
        print(f"  -> 输入 Prompt Tokens: {usage.prompt_tokens}")
        print(f"  -> 输出 Completion Tokens: {usage.completion_tokens}")
        print(f"  -> 本次调用总计消耗 Tokens: {usage.total_tokens}")
        
        return answer

# ==============================================================================
# 本地测试与离线模拟
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("=== Langfuse Agent 生产可观测性与 APM 链路追踪演示 ===")
    print("=" * 60)

    test_user = "usr_frontend_dev_1001"
    test_query = "请用 3 句话总结前端开发者转型 AI Agent 的最大核心竞争优势。"

    if not os.getenv("OPENAI_API_KEY"):
        print("\n[提示] 检测到当前系统未设置 OPENAI_API_KEY 环境变量。")
        print("以下展示生产监控链路捕获到的预期元数据拓扑结构：")
        print("----------------------------------------------------------------------")
        print(f"1. 追踪名称 (Trace Name): agent-architecture-consulting")
        print(f"2. 租户用户 (User ID): {test_user}")
        print(f"3. 注入标签 (Tags): ['production', 'frontend-transform', 'q3-demo']")
        print(f"4. 模拟消耗统计:")
        print(f"   - Prompt Tokens: 48 (约 $0.00012)")
        print(f"   - Completion Tokens: 125 (约 $0.00125)")
        print(f"   - 端到端总延迟 (Latency): 1.42s (首字延迟 TTFT: 320ms)")
        print(f"5. 模型生成内容预览:")
        print(f"   ① 拥有敏锐的交互感知与全栈组件思维，能将 Agent 的抽象思考转化为直观的 Generative UI；")
        print(f"   ② 擅长事件驱动与流式响应（SSE/WebSocket），在前后端协作体验上具有天然优势；")
        print(f"   ③ 从用户体验出发设计 Agent 工具链，更容易做出高可用、符合真实人机交互直觉的 AI 产品。")
        print("----------------------------------------------------------------------")
        print("登录 Langfuse 控制台即可查看每一步的瀑布流甘特图与 Token 成本实时汇总！\n")
    else:
        try:
            demo = AgentObservabilityDemo()
            result = demo.run_monitored_workflow(test_user, test_query)
            print(f"\n模型生成内容:\n{result}")
        except Exception as e:
            print(f"[执行异常]: {e}")
