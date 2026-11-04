# DAY 07：Prompt 进阶与强制结构化输出（Structured Outputs）

> **目标**：彻底告别“请以 JSON 格式输出，不要输出其他文字”这种靠运气约束模型的低级做法，掌握工业级 **Structured Outputs 语法约束解码**。

---

## 1. 传统 JSON Prompt 的痛点

过去开发者最常写的 Prompt：
```markdown
请分析这段文字，提取出其中的手机号和姓名，以 JSON 格式输出，不要包含 markdown 标记！
```
**为什么这在生产环境极度脆弱？**
1. 大模型经常自作主张加上 ` ```json ` 代码块包裹；
2. 偶尔在前后加上“好的，这是为您提取的信息：”导致 `JSON.parse()` 直接抛出 SyntaxError；
3. 遇到多层复杂嵌套时，大模型可能漏掉必填 key，或者将数字格式化为字符串。

---

## 2. 什么是现代 Structured Outputs？

OpenAI、Gemini、DeepSeek 等主流大模型现在均支持 **Constrained Decoding（语法受限解码）**。
- **原理**：我们在请求时把 JSON Schema 传给推理引擎，引擎在逐个 Token 计算采样概率时，**直接将任何不符合 Schema 语法状态转移的 Token 概率强制置为 0**！
- **效果**：大模型 **100% 保证** 返回完全合法、字段齐全的 JSON，绝对不会解析失败。

---

## 3. 前端与 Agent 中的应用场景

1. **意图路由（Intent Classification）**：让大模型从固定的几个枚举类型中选择，返回对应的页面路由。
2. **表单自动化填充**：用户口述一段杂乱需求，模型精准填充表单各个输入框。
3. **Generative UI 参数下发**：模型决策渲染哪个前端卡片组件，并填入强类型 props。

---

## 🛠️ 今日对应实战源码
请阅读并运行以下源码，体会通过 Pydantic 强类型直接解析非结构化文本的威力：
- 结构化抽取实战：[`phase03-native-agent/day07_structured_output.py`](../phase03-native-agent/day07_structured_output.py)
