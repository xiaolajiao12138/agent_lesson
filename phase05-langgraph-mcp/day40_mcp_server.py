"""
DAY 40 实战源码：开发符合官方 MCP (Model Context Protocol) 规范的工具服务
==============================================================================
【文件导读】：
    在 MCP 出现之前，开发者要想让大模型调用一个本地工具，必须：
    - 给 OpenAI 写一套 Function Calling；
    - 给 LangChain 写一套 BaseTool；
    - 给 Claude 桌面版又写一套自定义工具... 极其碎片化且无法复用。

    MCP（模型上下文协议，Model Context Protocol）是由 Anthropic 提出、现已成为全行业开放标准的统一规范。
    它被誉为 **“AI 工具界的 Type-C 统一通用物理接口”**：
    你只需要用 MCP 协议暴露你的工具或数据库接口，所有的宿主客户端（Claude Desktop、Cursor、
    Antigravity IDE、以及各类自定义 LangGraph 智能体）都能开箱即用直接挂载！

【核心技术要点】：
    1. FastMCP 框架：官方提供的极简开发工具库，对标 FastAPI 之于 Web 接口的体验。
    2. @mcp.tool() 装饰器：自动反射 Python 函数签名、类型注解与 Docstring，生成标准 JSON-RPC 规范。
    3. 通信传输协议 (Transport)：
       - stdio（标准输入输出）：最轻量、宿主进程直接 fork 启动并管道通信，安全且免端口占用；
       - SSE（Server-Sent Events）：支持跨网络远程微服务化调用。

【运行要求】：
    pip install mcp
    python day40_mcp_server.py
==============================================================================
"""

from typing import List, Dict, Any

def create_mcp_app():
    from mcp.server.fastmcp import FastMCP

    # 1. 实例化标准 FastMCP 服务对象
    # 参数为该 MCP Server 在生态系统中的唯一服务命名
    mcp = FastMCP("Frontend-DevTools-MCP-Server")

    # ==========================================================================
    # 2. 使用 @mcp.tool() 暴露工具给大模型
    # ==========================================================================

    @mcp.tool()
    def inspect_package_version(package_name: str) -> Dict[str, str]:
        """
        检查指定前端或 Python 依赖包的推荐生产环境稳定版本与安全审计状态。
        
        参数:
            package_name: 依赖包名称，例如 'react', 'next', 'fastapi', 'langgraph'
        """
        # 模拟内部依赖白名单与安全审计数据库
        package_catalog = {
            "react": {"latest": "19.0.0", "status": "stable", "license": "MIT"},
            "next": {"latest": "15.1.0", "status": "stable", "license": "MIT"},
            "fastapi": {"latest": "0.115.0", "status": "stable", "license": "MIT"},
            "langgraph": {"latest": "0.2.45", "status": "recommended", "license": "MIT"},
            "pydantic": {"latest": "2.10.0", "status": "stable", "license": "MIT"}
        }
        
        key = package_name.lower().strip()
        if key in package_catalog:
            info = package_catalog[key]
            return {
                "package": package_name,
                "version": info["latest"],
                "security_audit": "PASSED (无已知高危 CVE 漏洞)",
                "status": info["status"]
            }
        return {
            "package": package_name,
            "version": "unknown",
            "security_audit": "未在官方推荐白名单中找到该包，请谨慎评估后安装"
        }

    @mcp.tool()
    def calculate_bundle_size_impact(added_lines_of_code: int, has_heavy_dependency: bool = False) -> str:
        """
        预估前端新增代码与第三方重型依赖对最终打包体积 (Bundle Size) 的增量影响。
        
        参数:
            added_lines_of_code: 预计新增的代码有效行数
            has_heavy_dependency: 是否引入了重型三方库（如 moment.js 或 lodash 全量包）
        """
        base_kb = (added_lines_of_code * 0.05) # 预估每行源码经压缩混淆后增加约 0.05 KB
        if has_heavy_dependency:
            base_kb += 75.0 # 重型第三方库的额外打包开销
            
        return f"预估打包体积增量约为: {base_kb:.2f} KB (Gzip 压缩后)。建议：优先按需引入 (Tree-shaking)。"

    return mcp

# ==============================================================================
# 3. 启动标准通信服务
# ==============================================================================

if __name__ == "__main__":
    try:
        mcp_app = create_mcp_app()
        print("=" * 60)
        print("[就绪] 标准 MCP (Model Context Protocol) 工具服务初始化完毕！")
        print("支持接入: Claude Desktop, Cursor, Antigravity, Custom Agent Client")
        print("传输协议: 标准输入输出 (stdio) JSON-RPC 2.0 监听中...")
        print("=" * 60)
        
        # 采用标准 stdio 作为传输层（MCP 最通用的一种通信协议）
        mcp_app.run(transport="stdio")

    except ImportError:
        print("[提示] 本地未安装 mcp 官方依赖，可执行: pip install mcp 进行安装体验。")
