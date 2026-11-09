"""
全项目通用大模型环境配置中心
==============================================================================
说明：
    统一管理大模型的 API Key、Base URL 以及模型名称。
    所有 Phase 的代码都可以直接引用本模块，开箱即用，无需到处重复硬编码。
==============================================================================
"""

import os
from openai import OpenAI, AsyncOpenAI

# 默认全局配置（优先读取系统环境变量，如无则使用用户配置的默认值）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://sub2api.starysp.top/v1")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-6.1-sol")

# 同步写入当前进程环境变量，确保三方库（如 LangGraph, Langfuse 等）也能自动识别
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL
os.environ["OPENAI_MODEL_NAME"] = DEFAULT_MODEL

def get_openai_client() -> OpenAI:
    """获取预先配置好的同步 OpenAI 客户端"""
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

def get_async_openai_client() -> AsyncOpenAI:
    """获取预先配置好的异步 OpenAI 客户端"""
    return AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

