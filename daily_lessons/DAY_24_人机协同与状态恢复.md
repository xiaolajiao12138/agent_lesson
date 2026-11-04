# DAY 24 ~ DAY 29：人机协同（Human-in-the-loop）与状态持久化

> **目标**：掌握在复杂 Agent 中实现“执行挂起、保存会话快照、等待人工审核、外部唤醒恢复”的生产级机制。

---

## 1. 为什么“人在回路”是 Agent 商业化落地的必须项？

很多初学者误以为 Agent 必须是 100% 全自动的。但现实世界中：
- 自动给全体客户发公关邮件？**风险极高，必须人工 Review 文案！**
- 自动给用户退款 100 万元？**违规高危，必须主管批准！**
- 自动执行数据库 DROP TABLE 指令？**致命灾难！**

因此，**“人机协同（Human-in-the-loop）”是企业敢把 Agent 接入生产核心系统的唯一前提**。

---

## 2. 状态挂起与恢复的运行机制

```mermaid
sequenceDiagram
    autonumber
    actor Dev as 前端开发者
    participant App as LangGraph 状态图引擎
    participant Checkpoint as 状态检查点 (MemorySaver / Redis)
    actor Admin as 管理员 / 审计员

    Dev->>App: 提交敏感任务（如大额支付申请）
    App->>App: 执行前置节点，生成执行计划
    App->>Checkpoint: 到达敏感节点前，自动持久化当前会话快照
    App-->>Dev: 工作流挂起（Status: Pending Approval）
    
    Note over App,Admin: 时间流逝... 可以是 10 秒后，也可以是 3 天后

    Admin->>App: 审查待执行参数，在管理界面点击【批准】
    App->>Checkpoint: 根据会话 Thread ID 读取被冻结的历史状态
    App->>App: 合并管理员审批字段（human_approved = True）
    App->>App: 恢复向下流转，执行核心动作
    App-->>Dev: 交付最终执行结果
```

---

## 🛠️ 今日对应实战源码
- 人机协同打断与检查点恢复实战：[`phase05-langgraph-mcp/day24_human_in_the_loop.py`](../phase05-langgraph-mcp/day24_human_in_the_loop.py)
