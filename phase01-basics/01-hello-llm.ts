import "dotenv/config";
import OpenAI from "openai";

// ============================================================================
// 1. 读取环境变量与初始化客户端
// ============================================================================
// LLM_API_KEY: 访问大模型服务的“身份凭证/密码”
const apiKey = process.env.LLM_API_KEY;

// LLM_BASE_URL: 模型服务商的 API 基础网关地址
// 无论是 OpenAI 官方、DeepSeek、月之暗面(Kimi)、零一万物，还是中转聚合API，只要支持 OpenAI 兼容格式，填对应的网关即可
const baseURL = process.env.LLM_BASE_URL || "https://api.deepseek.com";

// LLM_MODEL: 具体调用的模型版本名称（如 gpt-4o, deepseek-chat, claude-3-5-sonnet 等）
const model = process.env.LLM_MODEL || "deepseek-chat";

// 安全校验：避免没有配置 Key 时发起无效网络请求
if (!apiKey || apiKey === "your_api_key_here") {
  console.error("❌ 错误：未检测到有效的 API Key！");
  console.log("👉 请先打开 .env 文件，填入你的 LLM_API_KEY 后再运行此脚本。");
  process.exit(1);
}

/**
 * OpenAI 构造函数常用配置项：
 * - apiKey: 认证 Token（必填）
 * - baseURL: 接口基础路径（选填，默认是官方 https://api.openai.com/v1）
 * - timeout: 请求超时时间（毫秒），默认 10 分钟。Agent 项目中常设为 30000~60000ms
 * - maxRetries: 遇 429(限流) 或 5xx(服务故障) 时的自动重试次数，默认 2 次
 */
const client = new OpenAI({
  apiKey: apiKey,
  baseURL: baseURL,
  timeout: 60 * 1000, // 超时时间：60秒
  maxRetries: 2,       // 网络抖动时自动重试 2 次
});

async function main() {
  console.log("🤖 正在连接大模型服务器...");
  console.log(`📡 Base URL: ${baseURL}`);
  console.log(`🎯 调用模型: ${model}\n`);

  try {
    const startTime = Date.now();

    // ============================================================================
    // 2. 发起 Chat Completions 请求
    // ============================================================================
    const response = await client.chat.completions.create({
      // 【必须】指定调用的模型名称
      model: model,

      // 【核心控制】temperature（采样温度）：控制输出的随机性和发散程度
      // 取值范围：0.0 ~ 2.0，默认一般为 1.0
      // - 0.0 ~ 0.2: 极度保守严谨，每次回答基本完全一致，适合【代码生成、JSON提取、SQL转换、业务规则判断】
      // - 0.7 ~ 0.8: 常用平衡点，兼具逻辑性与语言丰富度，适合【日常对话、通用问答、客服回复】
      // - 1.2 ~ 1.5: 极富想象力、多变，适合【头脑风暴、故事创作、文案起标题】
      temperature: 0.7,

      // 【对话历史与上下文】messages 数组
      // 模型没有长期记忆，每一轮对话必须把历史一并发过去，消息按从早到晚的时序排列
      messages: [
        /**
         * role: "system"（系统指令/人设）
         * 作用：最高优先级指令。定义模型的身份、性格、行为准则、安全红线。通常放在 messages 数组第 0 位。
         */
        {
          role: "system",
          content: "你是一个幽默、专业的资深架构师导师，正在指导一名优秀的前端工程师转型为 AI Agent 工程师。",
        },
        /**
         * role: "user"（人类用户输入）
         * 作用：用户的实际提问或操作请求。
         */
        {
          role: "user",
          content: "今年是什么生肖年",
        },
        /**
         * 【其他可选 role 角色补充】：
         * - role: "assistant": 模型之前回复的历史内容（做多轮连续对话时需要回传）。
         * - role: "tool" 或 "function": 工具/函数执行完后返回给模型的结果（进阶 Agent 工具调用时使用）。
         */
      ],

      // ========================================================================
      // 💡【常用其他核心字段扩展科普】（当前使用默认值，需要时可解开）：
      // ========================================================================

      // max_tokens: 限制模型单次回答生成的【最大 Token 数量】。防止模型无节制输出消耗巨额费用或超时。
      // max_tokens: 1500,

      // top_p: 核采样概率（0.0 ~ 1.0）。另一种控制多样性的方式，模型只在累积概率达到 top_p 的词汇中选词。
      // 业界建议：temperature 和 top_p 二选一调整，通常调 temperature，保持 top_p: 1.0。
      // top_p: 1.0,

      // presence_penalty: 存在惩罚（-2.0 ~ 2.0）。正值会鼓励模型引入新话题，避免重复讲过的话题。
      // presence_penalty: 0.0,

      // frequency_penalty: 频率惩罚（-2.0 ~ 2.0）。正值会惩罚那些高频出现的具体单词，减少字词自我重复复读。
      // frequency_penalty: 0.0,

      // stop: 停止词序列（字符串或数组）。一旦模型即将输出指定字符串，立刻强行刹车截断停止。
      // 例如：stop: ["【结束】", "用户:"]

      // seed: 随机数种子（整数）。配合 temperature: 0，尽量保证多次请求返回一模一样的结果，常用于单元测试复现。
      // seed: 42,
    });

    const elapsed = Date.now() - startTime;

    // ============================================================================
    // 3. 解析模型返回的数据结构 (response)
    // ============================================================================
    /**
     * response.choices: 模型返回的候选列表（数组）
     * 为什么是数组？因为可以通过配置参数 `n: 2` 让模型一次性生成多个回答供用户挑选，默认 n=1，取 choices[0] 即可。
     */
    const choice = response.choices[0];

    console.log("==================== [模型回复] ====================");
    /**
     * choice.message: 包含 role ("assistant") 和 content (生成的正文内容)
     */
    console.log(choice.message.content);
    console.log("====================================================");

    // 4. 统计指标与关键字段解析
    console.log("\n📊 [本次调用性能与消耗统计]");
    console.log(`⏱️ 响应耗时: ${elapsed} ms`);

    /**
     * response.usage: Token 消耗统计对象
     * - prompt_tokens: 输入消耗 Token（你的 system + user 消息 + 内部模板转换）
     * - completion_tokens: 输出消耗 Token（模型回复正文的词元数）
     * - total_tokens: 总消耗 = prompt_tokens + completion_tokens
     */
    console.log(`📥 输入消耗 Token (Prompt): ${response.usage?.prompt_tokens}`);
    console.log(`📤 输出消耗 Token (Completion): ${response.usage?.completion_tokens}`);
    console.log(`💰 总计消耗 Token (Total): ${response.usage?.total_tokens}`);

    /**
     * choice.finish_reason: 模型停止生成的原因
     * - "stop": 正常自然结束（回答完毕，最常见的正常状态）
     * - "length": 触发了 max_tokens 上限，回答被强行腰斩截断
     * - "tool_calls": 模型决定调用外部工具/函数，正在等待我们执行工具（Agent 核心状态）
     * - "content_filter": 触发了安全合规过滤策略，内容被拦截
     */
    console.log(`🏁 结束原因 (Finish Reason): ${choice.finish_reason}`);

  } catch (error: any) {
    // 异常捕获与常见 HTTP 状态码解读
    console.error("❌ 请求失败:", error.message || error);
    if (error.status === 401) {
      console.error("👉 401 Unauthorized: API Key 无效或过期，请检查 .env。");
    } else if (error.status === 429) {
      console.error("👉 429 Rate Limit: 账户欠费、超出频次限制（RPM/TPM）或并发过高。");
    } else if (error.status === 500 || error.status === 503) {
      console.error("👉 5xx Server Error: 模型服务商服务端繁忙或发生故障，建议自动重试。");
    }
  }
}

// 启动执行
main();

