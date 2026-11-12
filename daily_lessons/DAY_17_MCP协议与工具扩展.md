# DAY 17：MCP 协议与企业级可观测性

> **目标**：掌握 Anthropic 推动的 Model Context Protocol（模型上下文协议）行业标准，以及如何通过 Langfuse 实现生产级的 Trace、Cost 与 Latency 审计。

---

## 1. 什么是 MCP（Model Context Protocol）？

在过去，每个 Agent 框架都有自己的工具格式（OpenAI Tools、LangChain Tools、CrewAI Tools）。
这导致：如果你写了一个“查询企业 ERP”的工具，给 Claude 用要写一套适配，给 Cursor 用要写一套适配，给自己的 Agent 用又要写一套。

**MCP 的使命就是成为 AI 时代的“USB-C 接口”**：
- **MCP Server**：数据和工具的提供者（数据库、文件系统、API）。
- **MCP Client / Host**：任何支持 MCP 的宿主（Claude Desktop、Cursor、你自研的 Agent）。
- 协议底层基于 JSON-RPC 2.0，双方只需遵循一套规范，即可即插即用！

---

## 2. 为什么生产环境必须接 Langfuse？

一个没有接入 APM 监控的 Agent 在生产上就像在黑夜中盲跑：
1. **Token 成本控制**：精准看到每个功能、每个用户每天消耗了多少美元，哪些 Prompt 过于冗长。
2. **时延瓶颈分析**：查看一次复杂的 Agent 循环中，究竟是向量检索慢（耗时 2s），还是大模型生成慢（耗时 8s），还是工具 API 响应慢。
3. **Bad Case 回溯与 Evals**：当用户点踩时，能一键调出完整的上下文（System Prompt + 历史对话 + 工具入参），用来持续优化迭代。

---

## 🛠️ 今日对应实战源码
- 官方规范 MCP 工具服务开发：[`phase05-langgraph-mcp/day40_mcp_server.py`](../phase05-langgraph-mcp/day40_mcp_server.py)
- Langfuse 生产链路追踪监控：[`phase05-langgraph-mcp/day43_langfuse_observability.py`](../phase05-langgraph-mcp/day43_langfuse_observability.py)
