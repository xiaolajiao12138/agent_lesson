"""
DAY 18 实战源码：Agent 链路追踪与生产可观测性（基于 Langfuse）
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
    pip install langfuse openai python-dotenv
    python day18_langfuse_observability.py
==============================================================================
"""

import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# ==============================================================================
# 1. 配置环境与 API Key（支持本地 .env 与直接默认值注入）
# ==============================================================================

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 优先尝试从根目录或当前目录的 .env 文件加载
load_dotenv(os.path.join(parent_dir, ".env"), override=True)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

# OpenAI / 代理配置
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

# 注入系统环境变量（供 OpenAI 官方 SDK 读取）
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL
os.environ["OPENAI_API_BASE"] = OPENAI_BASE_URL

# ==============================================================================
# 2. Langfuse 云端面板三要素（可直接在 .env 里写，也可在代码里配置）
# ==============================================================================
# 登录 https://cloud.langfuse.com -> Project Settings -> API Keys 获取：
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-06978b08-2d1a-432c-b106-50a6ed815ecc")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-85596d51-216b-4d31-89d2-771dad2898c6")
os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


# ==============================================================================
# 生产级链路追踪客户端封装
# ==============================================================================

class AgentObservabilityDemo:
    """
    智能体生产级全链路监控示例
    """

    def __init__(self):
        pass

    def run_monitored_workflow(self, user_id: str, query: str):
        """
        发起一次被全链路打标、监控与计费的 Agent 推理调用
        """
        from langfuse.openai import OpenAI as TracedOpenAI
        
        # TracedOpenAI 是官方 SDK 提供的透明代理包装：
        # 显式传入 api_key 与 base_url，底层会在后台异步且无侵入地收集延迟、Token 和 Trace
        traced_client = TracedOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )

        print(f"\n[APM 监控中] 收到终端用户 [{user_id}] 提问: {query}")
        print("⏳ 正在请求大模型生成内容，并自动记录 Trace 链路追踪元数据...")
        
        # 发起调用，并在额外参数中注入丰富的业务上下文标签
        response = traced_client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是一名精通现代 Web 架构与 Agent 的技术专家。"},
                {"role": "user", "content": query}
            ],
            # 【核心追踪元数据】：
            name="agent-architecture-consulting", # 本次 Trace 追踪名称
            user=user_id,                         # 终端用户标识（对标 OpenAI user 标准字段）
            # metadata={
            #     "tags": ["production", "frontend-transform", "q3-demo"],
            #     "client_framework": "Next.js 15",
            #     "request_origin": "Shanghai, China",
            #     "environment": "production"
            # }
        )

        answer = response.choices[0].message.content
        
        # 打印使用量统计（SDK 已经自动为你计算并上报）
        usage = response.usage
        print("\n[监控埋点已成功生成]:")
        if usage:
            print(f"  -> 输入 Prompt Tokens: {usage.prompt_tokens}")
            print(f"  -> 输出 Completion Tokens: {usage.completion_tokens}")
            print(f"  -> 本次调用总计消耗 Tokens: {usage.total_tokens}")
        
        # 强制将本地队列中的 Trace 数据立即同步推送到云端（防止脚本退出导致数据丢失）
        try:
            from langfuse import Langfuse
            Langfuse().flush()
            print("🚀 [数据同步] Trace 链路追踪数据已成功推送至 Langfuse 云端！")
        except Exception:
            pass
        
        return answer

# ==============================================================================
# 本地测试与执行入口
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("=== Langfuse Agent 生产可观测性与 APM 链路追踪演示 ===")
    print("=" * 60)

    test_user = "usr_frontend_dev_1001"
    test_query = "请用 3 句话总结前端开发者转型 AI Agent 的最大核心竞争优势。"

    try:
        demo = AgentObservabilityDemo()
        result = demo.run_monitored_workflow(test_user, test_query)
        print(f"\n[模型实际生成内容]:\n{result}")
    except Exception as e:
        print(f"[执行异常]: {e}")
