import "dotenv/config";
import OpenAI from "openai";
import { z } from "zod";

// ============================================================================
// 1. 初始化客户端
// ============================================================================
const apiKey = process.env.LLM_API_KEY;
const baseURL = process.env.LLM_BASE_URL || "https://api.deepseek.com";
const model = process.env.LLM_MODEL || "deepseek-chat";

if (!apiKey || apiKey === "your_api_key_here") {
  console.error("❌ 错误：未检测到有效的 API Key！请先在 .env 中配置。");
  process.exit(1);
}

const client = new OpenAI({ apiKey, baseURL });

// ============================================================================
// 2. 用 Zod 定义严谨的业务数据模式 (Schema)
// ============================================================================
/**
 * 为什么需要 Zod？
 * TypeScript 的 interface 只是编译期检查，浏览器/Node 运行期会被完全抹去。
 * 大模型返回的是一段不确定的外部网络字符串，直接 JSON.parse() 如果字段缺失或类型错误（比如传了 null 或字符串类型的数字），
 * 前端在渲染组件（如 v-for="item in data.suggestions"）时就会直接崩掉（Uncaught TypeError: Cannot read properties of undefined）。
 * 
 * Zod 提供了【运行时校验 + 自动推导 TS 类型】的双重保障！
 */
const BugReportSchema = z.object({
  // .describe() 会作为文档注释，在进阶强约束模式下还会直接作为 Schema 的描述传给模型理解语义
  component: z.string().describe("出问题的组件或文件路径"),
  severity: z.enum(["low", "medium", "high", "critical"]).describe("严重等级枚举"),
  issueSummary: z.string().describe("问题本质一句话总结"),
  rootCause: z.string().describe("产生 Bug 的底层原因分析"),
  suggestions: z.array(z.string()).describe("给前端开发者的具体修复步骤列表"),
  estimatedMinutesToFix: z.number().describe("预估修复该问题所需要的耗时(分钟)"),
});

// 利用 z.infer 自动提取纯正的 TypeScript 类型定义，供后续业务代码享受类型推导
type BugReport = z.infer<typeof BugReportSchema>;

async function main() {
  console.log("🧩 正在测试【结构化输出 (Structured Output)】...\n");

  // 模拟一段前端开发者常见的真实 Bug 场景
  const problemDescription = `
    我们在 React 页面中使用 useEffect 监听 window 的 resize 事件：
    useEffect(() => {
      window.addEventListener('resize', () => {
        setDimensions({ width: window.innerWidth, height: window.innerHeight });
      });
    }, []);
    但在频繁切换路由后，页面变得越来越卡，甚至控制台偶尔报错内存溢出。
  `;

  try {
    // ============================================================================
    // 3. 发起请求并强制开启 JSON 模式
    // ============================================================================
    const response = await client.chat.completions.create({
      model: model,

      /**
       * 【核心参数】temperature: 0.1
       * ⚠️ 关键经验法则：
       * 做数据提取、格式化转换、结构化输出时，temperature 必须越低越好（0 或 0.1）。
       * 温度过高（如 1.0）会导致模型在 key 名或数据类型上“自由发挥”，破坏 JSON 结构！
       */
      temperature: 0.1,

      /**
       * 【核心参数】response_format: { type: "json_object" }
       * 作用：指示大模型启用 JSON 模式，确保返回的内容是一段语法合法的 JSON 字符串。
       * ⚠️ 重要规则：当启用此字段时，OpenAI 官方规范要求【messages 中必须出现 "JSON" 这个单词】，否则会报错 400！
       */
      response_format: { type: "json_object" },

      messages: [
        {
          role: "system",
          content: `你是一个资深前端专家与静态分析引擎。
请分析用户提供的前端 Bug，并以严格的 JSON 格式输出，不要包含任何额外的问候语或 Markdown 格式。
输出的 JSON 必须符合以下规范：
{
  "component": string,
  "severity": "low" | "medium" | "high" | "critical",
  "issueSummary": string,
  "rootCause": string,
  "suggestions": string[],
  "estimatedMinutesToFix": number
}`,
        },
        {
          role: "user",
          content: `请分析以下前端代码问题：\n${problemDescription}`,
        },
      ],
    });

    const rawJson = response.choices[0].message.content || "{}";
    console.log("📥 模型返回的原始 JSON 字符串:");
    console.log(rawJson);

    // ============================================================================
    // 4. 双重防线：JSON 解析 + Zod 运行时强校验
    // ============================================================================
    // 第一步：反序列化为 JS 对象
    const rawObject = JSON.parse(rawJson);

    // 第二步：使用 Zod 进行严格 Schema 校验
    // 如果模型少传了 suggestions 字段，或者把 estimatedMinutesToFix 写成了字符串 "30"，Zod 会立即精准拦截抛错
    const parsedData: BugReport = BugReportSchema.parse(rawObject);

    console.log("\n✅ Zod 校验成功！已转换为前端组件可放心绑定的强类型对象：");
    console.dir(parsedData, { depth: null });

    // ============================================================================
    // 5. 模拟前端 UI 渲染消费
    // ============================================================================
    console.log("\n💡 [模拟前端 UI 卡片渲染]：");
    console.log(`--------------------------------------------------`);
    console.log(`🚨 等级: [${parsedData.severity.toUpperCase()}]`);
    console.log(`🎯 目标: ${parsedData.component}`);
    console.log(`📌 概览: ${parsedData.issueSummary}`);
    console.log(`🔍 根因: ${parsedData.rootCause}`);
    console.log(`⏱️ 预估: ${parsedData.estimatedMinutesToFix} 分钟`);
    console.log(`🛠️ 建议步骤:`);
    parsedData.suggestions.forEach((s, idx) => console.log(`   ${idx + 1}. ${s}`));
    console.log(`--------------------------------------------------`);

  } catch (error: any) {
    if (error instanceof z.ZodError) {
      // 捕获 Zod 校验失败：输出具体是哪个 key 不符合规范
      console.error("❌ 数据结构校验失败（模型返回字段不符合预期）:", error.errors);
    } else {
      console.error("❌ 请求或解析失败:", error.message || error);
    }
  }
}

main();

