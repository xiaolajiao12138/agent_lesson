"""
DAY 40 实战源码：开发符合官方 MCP (Model Context Protocol) 规范的工具服务
文件说明：
    MCP（模型上下文协议）由 Anthropic 推出，是目前大模型接入外部资源、文件与工具的
    行业统一开放标准。任何支持 MCP 的宿主（Claude Desktop、Cursor、自定义 Agent）
    都可以直接发现并调用通过 MCP 暴露的接口。
运行要求：
    pip install mcp
    python day40_mcp_server.py
"""

from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# 1. 实例化标准 FastMCP 服务对象
# ---------------------------------------------------------------------------
# 参数为该 MCP Server 在生态系统中的唯一名称
mcp = FastMCP("Frontend-DevTools-MCP-Server")

# ---------------------------------------------------------------------------
# 2. 使用 @mcp.tool() 暴露工具给大模型
# ---------------------------------------------------------------------------

@mcp.tool()
def inspect_package_version(package_name: str) -> Dict[str, str]:
    """
    检查指定 npm/pip 依赖包的推荐生产环境稳定版本与安全状态
    
    参数:
        package_name: 包名称，例如 'react', 'next', 'fastapi', 'langgraph'
    """
    # 模拟内部依赖元数据库
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
        "security_audit": "未在官方白名单中找到该包，请谨慎安装"
    }

@mcp.tool()
def calculate_bundle_size_impact(added_lines_of_code: int, has_heavy_dependency: bool = False) -> str:
    """
    预估前端新增代码与三方依赖对最终打包体积 (Bundle Size) 的增量影响
    
    参数:
        added_lines_of_code: 预计新增的代码有效行数
        has_heavy_dependency: 是否引入了重型三方库（如 moment.js 或 lodash 全量包）
    """
    base_kb = (added_lines_of_code * 0.05) # 预估每行代码压缩后增加约 0.05 KB
    if has_heavy_dependency:
        base_kb += 75.0 # 重型三方库额外开销
        
    return f"预估打包体积增量约为: {base_kb:.2f} KB (Gzip 压缩后)。建议：优先按需引入 (Tree-shaking)。"

# ---------------------------------------------------------------------------
# 3. 启动标准通信服务
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=======================================================")
    print("🚀 标准 MCP (Model Context Protocol) 工具服务已就绪！")
    print("支持接入: Claude Desktop, Cursor, Custom Agent MCP Client")
    print("正在通过标准输入输出 (stdio) 监听大模型宿主的调用握手...")
    print("=======================================================")
    
    # 采用标准 stdio 作为传输层（MCP 最通用的一种通信协议）
    mcp.run(transport="stdio")
