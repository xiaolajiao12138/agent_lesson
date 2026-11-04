import "dotenv/config";
import OpenAI from "openai";

// ============================================================================
// 1. 读取配置与初始化
// ============================================================================
const apiKey = process.env.LLM_API_KEY;
const baseURL = process.env.LLM_BASE_URL || "https://api.deepseek.com";
const model = process.env.LLM_MODEL || "deepseek-chat";

if (!apiKey || apiKey === "your_api_key_here") {
  console.error("❌ 错误：未检测到有效的 API Key！请先在 .env 中配置。");
  process.exit(1);
}

const client = new OpenAI({ apiKey, baseURL });

async function main() {
  console.log("🌊 正在以【流式（Streaming）】模式发起请求...\n");

  const startTime = Date.now();
  let firstTokenTime: number | null = null; // 用于记录首字到达时间（TTFT）
  let fullText = "";                        // 缓存完整的拼接文本

  try {
    // ============================================================================
    // 2. 发起流式请求 (关键参数: stream: true)
    // ============================================================================
    /**
     * 当 stream 设为 true 时：
     * client.chat.completions.create 不再返回普通的 Promise<ChatCompletion>，
     * 而是返回一个【异步可迭代流】 Stream<ChatCompletionChunk>。
     * 
     * 底层原理：基于 HTTP 协议的 SSE（Server-Sent Events，服务端推送事件）。
     * 服务端保持连接不断开，大模型每解码出 1~2 个 Token，就会像水龙头滴水一样推过来一个 data: {...} 数据包。
     */
    const stream = await client.chat.completions.create({
      model: model,
      temperature: 0.7,
      stream: true, // 【核心开关】：开启流式传输

      // 💡【流式进阶可选参数】：
      // stream_options: { include_usage: true }, // 很多模型（如 OpenAI/DeepSeek）支持在流的最后一个 chunk 返回 usage Token 统计

      messages: [
        {
          role: "system",
          content: "你是一名资深技术顾问，请简明扼要、条理清晰地回答技术问题。",
        },
        {
          role: "user",
          content: "请用 3 点说明：为什么现代 AI 交互必须使用流式输出（Streaming），而不是让用户等待完整结果？",
        },
      ],
    });

    console.log("==================== [流式打字机输出] ====================");

    // ============================================================================
    // 3. 消费流式数据（异步迭代器 for await...of）
    // ============================================================================
    /**
     * for await (const chunk of stream) 是 ES2018 引入的异步迭代语法：
     * 只要服务端推送了一个新的小数据块（chunk），循环体就会立刻执行一次。
     */
    for await (const chunk of stream) {
      /**
       * 注意与普通非流式的重大区别：
       * - 非流式：choice.message.content（拿到的是完整的完整字符串）
       * - 流式：choice.delta.content（delta 代表增量！每次只有这 1 个字或词）
       */
      const content = chunk.choices[0]?.delta?.content || "";

      if (content) {
        // 第一次拿到文字时，计算 TTFT（Time To First Token）
        if (firstTokenTime === null) {
          firstTokenTime = Date.now() - startTime;
        }

        // process.stdout.write 类似于 console.log，但它【不会自动换行】
        // 这样增量文字就会紧挨着一个个打印在终端上，形成逼真的打字机效果
        process.stdout.write(content);

        // 前端通常用 ref/响应式变量累计字符串：chatMessage.value += content;
        fullText += content;
      }

      // 如果开启了 stream_options: { include_usage: true }，在最后一个 chunk 能取到 chunk.usage
    }

    const totalElapsed = Date.now() - startTime;

    console.log("\n==========================================================");
    // ============================================================================
    // 4. 前端交互核心指标解析
    // ============================================================================
    console.log("\n📊 [流式传输性能体验分析]");
    /**
     * TTFT (Time To First Token) 是 AI 产品前端体验的“生死指标”：
     * - 如果 TTFT < 1000ms：用户感觉“几乎秒回”，体验极佳
     * - 如果 TTFT > 3000ms：用户开始感到焦虑和等待
     */
    console.log(`⚡ 首字响应时间 (TTFT - Time To First Token): ${firstTokenTime} ms`);
    console.log(`⏱️ 完整生成总耗时: ${totalElapsed} ms`);
    console.log(`📝 生成总字符数: ${fullText.length} 字`);

  } catch (error: any) {
    console.error("\n❌ 请求失败:", error.message || error);
  }
}

main();

