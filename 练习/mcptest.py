
def test():
    from mcp.server.mcpserver import MCPServer as FastMCP
    mcp = FastMCP("Frontend-DevTools-MCP-Server")
    @mcp.tool()
    def test1(name:str)->str:
        """获取名字 参数：name：姓名"""
        return name
    return mcp


if __name__ == "__main__":
    import asyncio
    # async def test_mcp():
    mcp = test()
        # res1=await mcp.call_tool('test1',{
        #     "name":"张三"
        # })
        # print(res1.content[0].text)
    mcp.run(transport="stdio")
    # asyncio.run(test_mcp())