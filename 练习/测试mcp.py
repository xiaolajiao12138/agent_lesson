


import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 1. 指定你要连接的外部 MCP 脚本路径
    server_params = StdioServerParameters(
        command="python",
        args=["练习/mcptest.py"],  # 👈 客户端会自动在后台启动你的 mcptest.py！
    )

    # 2. 接通管道 (read 读返回, write 发指令)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 握手初始化
            await session.initialize()

            # 👉 发指令 1：询问 mcptest.py 里有哪些工具？
            tools_res = await session.list_tools()
            print("成功连上服务端，发现工具：", [t.name for t in tools_res.tools])

            # 👉 发指令 2：隔空调用 mcptest.py 里的 test1 函数！
            result = await session.call_tool("test1", arguments={"name": "张三"})
            print("收到 mcptest.py 返回结果：", result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
