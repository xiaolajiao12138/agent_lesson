"""真实 OpenAI 兼容客户端工厂；仅创建客户端，不替你实现问答接口。

知识对应：SDK 初始化、配置依赖、异步资源清理。
客户端不会伪造模型回答，也不会在启动时自动调用收费接口。
"""
from openai import AsyncOpenAI, OpenAI

from .config import Settings


def _client_options(settings: Settings) -> dict:
    if not settings.model_configured:
        raise RuntimeError("请配置 OPENAI_API_KEY 和 OPENAI_MODEL_NAME")
    return dict(api_key=settings.openai_api_key, base_url=settings.openai_base_url,
                timeout=settings.model_timeout, max_retries=1)


def create_async_openai_client(settings: Settings) -> AsyncOpenAI:
    """供 async def 接口使用：调用模型时需要 await；结束时 await client.close()。"""
    return AsyncOpenAI(**_client_options(settings))


def create_openai_client(settings: Settings) -> OpenAI:
    """供同步脚本使用；不要在 async def 中直接执行同步网络请求。"""
    return OpenAI(**_client_options(settings))
