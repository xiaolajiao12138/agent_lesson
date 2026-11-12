/**
 * DAY 47 实战源码：全栈 Agent 前端 —— 流式消费与 Generative UI 动态组件渲染
 * ==============================================================================
 * 【文件导读】：
 *   传统的前端 AI 聊天机器人（如市面上最简单的 ChatGPT 套壳应用）只负责把文本一行行打出来。
 *   在真实的高级 Agent 全栈工程中，纯文本交互已经无法满足复杂业务场景！
 * 
 *   【Generative UI（生成式 UI）的核心革命】：
 *   大模型与后端 Agent 吐出的不仅是 Markdown 字符串，而是**带有明确组件协议的结构化 JSON**！
 *   前端通过 EventSource 监听自定义 SSE 多事件管道：
 *   1. 接收到 'thought' 事件       -> 渲染思考链手风琴面板；
 *   2. 接收到 'tool_call' 事件     -> 渲染工具调度进度日志；
 *   3. 接收到 'generative_ui' 事件 -> 动态实例化并挂载真实的 React 交互式卡片（支持点击、按钮、交互）；
 *   4. 接收到 'message_chunk' 事件 -> 渲染常规流式打字机文本。
 * 
 * 【技术栈规范】：
 *   React 18/19 + TypeScript + Tailwind CSS
 * ==============================================================================
 */

import React, { useState, useEffect, useRef } from 'react';

// ==============================================================================
// 1. 类型契约定义（严格对标后端 FastAPI 下发的 SSE JSON Schema）
// ==============================================================================

/**
 * 动态指标卡片组件的属性契约
 * 对应后端 generative_ui 事件中的 props 字典
 */
interface MetricCardProps {
  title: string;             // 卡片标题，如 '2026 新能源出海核心态势简报'
  penetration_rate: string;  // 产业渗透率指标
  export_growth: string;     // 出口增长率
  risk_warning: string;      // 关键风险警示提示
  tags: string[];            // 业务分类标签数组
}

/**
 * Agent 思考链事件载荷
 */
interface ThoughtEvent {
  stage: string;             // 思考所处阶段，如 'intent_understanding'
  message: string;           // 具体的思考说明文本
}

/**
 * 外部工具调度日志载荷
 */
interface ToolEvent {
  tool_name: string;         // 被调度的工具名称，如 'fetch_industry_report'
  status: 'executing' | 'completed'; // 执行状态：执行中 | 已完成
  summary?: string;          // 执行完成后的结果简报
}

// ==============================================================================
// 2. 动态生成的 UI 卡片组件 (Generative UI Component)
// ==============================================================================
// 这不是静态死代码，而是后端 Agent 根据检索到的新能源数据，在运行时动态决定渲染的高级交互组件！
// 它自带独立的 useState 状态，用户可以在卡片上直接点击“加入大盘自选”或“已订阅”。

export const MetricDashboardCard: React.FC<MetricCardProps> = ({
  title,
  penetration_rate,
  export_growth,
  risk_warning,
  tags,
}) => {
  // 组件自身的独立交互状态
  const [isFollowed, setIsFollowed] = useState(false);

  return (
    <div className="my-4 p-5 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 shadow-sm transition-all hover:shadow-md">
      {/* 卡片头部：标题与动态组件角标 */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></span>
          {title}
        </h3>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">
          Generative UI 动态组件
        </span>
      </div>

      {/* 核心指标栅格：将原本生硬的数据用现代仪表盘视觉呈现 */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-2xs">
          <div className="text-xs text-gray-500 mb-1">产业渗透率</div>
          <div className="text-2xl font-black font-mono text-indigo-600">{penetration_rate}</div>
        </div>
        <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-2xs">
          <div className="text-xs text-gray-500 mb-1">海外出口同比</div>
          <div className="text-2xl font-black font-mono text-emerald-600">{export_growth}</div>
        </div>
      </div>

      {/* 风险提示栏 */}
      <div className="text-xs text-amber-800 bg-amber-50/80 p-2.5 rounded-lg border border-amber-200/60 mb-3">
        <strong>[风险关注]</strong> {risk_warning}
      </div>

      {/* 底部操作栏：支持用户实时点击与组件交互 */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <div className="flex gap-1.5 flex-wrap">
          {tags.map((t, idx) => (
            <span key={idx} className="text-[11px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded-md">
              #{t}
            </span>
          ))}
        </div>
        <button
          onClick={() => setIsFollowed(!isFollowed)}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
            isFollowed
              ? 'bg-emerald-600 text-white'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
          }`}
        >
          {isFollowed ? '✓ 已订阅监控' : '+ 加入大盘自选'}
        </button>
      </div>
    </div>
  );
};

// ==============================================================================
// 3. 主界面容器与多事件 SSE 消费逻辑 (Agent Terminal)
// ==============================================================================

export const AgentStreamingTerminal: React.FC = () => {
  // 用户输入的任务需求文本
  const [userPrompt, setUserPrompt] = useState('分析 2026 年新能源汽车出海战略');
  // 是否正在执行流式推理
  const [isRunning, setIsRunning] = useState(false);

  // 多通道状态解耦：
  // 思考、工具日志、动态卡片、打字机文字各自独立更新，互不阻塞重渲染
  const [thoughts, setThoughts] = useState<ThoughtEvent[]>([]);
  const [toolLogs, setToolLogs] = useState<ToolEvent[]>([]);
  const [generativeCards, setGenerativeCards] = useState<MetricCardProps[]>([]);
  const [streamedText, setStreamedText] = useState('');

  // 保持对 EventSource 实例的引用，便于在卸载或出错时优雅切断
  const eventSourceRef = useRef<EventSource | null>(null);

  /**
   * 触发启动 Agent 任务并连接后端 SSE 管道
   */
  const handleStartTask = () => {
    if (isRunning) return;

    // 1. 初始化清空历史状态
    setIsRunning(true);
    setThoughts([]);
    setToolLogs([]);
    setGenerativeCards([]);
    setStreamedText('');

    // 2. 建立原生浏览器 EventSource 长连接（跨端口连接后端 FastAPI）
    const url = `http://127.0.0.1:8000/api/agent/stream?prompt=${encodeURIComponent(userPrompt)}`;
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    // -------------------------------------------------------------------------
    // 监听通道 1：思考链过程事件 ('thought')
    // -------------------------------------------------------------------------
    sse.addEventListener('thought', (e: MessageEvent) => {
      const data: ThoughtEvent = JSON.parse(e.data);
      setThoughts((prev) => [...prev, data]);
    });

    // -------------------------------------------------------------------------
    // 监听通道 2：工具调度日志事件 ('tool_call')
    // -------------------------------------------------------------------------
    sse.addEventListener('tool_call', (e: MessageEvent) => {
      const data: ToolEvent = JSON.parse(e.data);
      setToolLogs((prev) => [...prev, data]);
    });

    // -------------------------------------------------------------------------
    // 监听通道 3：【核心】Generative UI 动态结构体事件 ('generative_ui')
    // -------------------------------------------------------------------------
    sse.addEventListener('generative_ui', (e: MessageEvent) => {
      const payload = JSON.parse(e.data);
      // 根据后端指定的 component_type 决定挂载哪个 React 组件
      if (payload.component_type === 'MetricDashboardCard') {
        setGenerativeCards((prev) => [...prev, payload.props]);
      }
    });

    // -------------------------------------------------------------------------
    // 监听通道 4：最终建议文字打字机流 ('message_chunk')
    // -------------------------------------------------------------------------
    sse.addEventListener('message_chunk', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setStreamedText((prev) => prev + data.delta);
    });

    // -------------------------------------------------------------------------
    // 监听通道 5：任务结束信号 ('done')
    // -------------------------------------------------------------------------
    sse.addEventListener('done', () => {
      console.log('[SSE] 后端 Agent 工作流推送完毕，安全断开长连接。');
      sse.close();
      setIsRunning(false);
    });

    // 异常兜底监听
    sse.onerror = (err) => {
      console.error('[SSE] 通信发生异常或服务主动终止:', err);
      sse.close();
      setIsRunning(false);
    };
  };

  /**
   * 组件生命周期钩子：卸载时切断未关闭的长连接，杜绝内存泄漏
   */
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="max-w-3xl mx-auto my-8 p-6 bg-white rounded-3xl shadow-xl border border-gray-100 font-sans">
      {/* 顶部标题区 */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
        <div>
          <h2 className="text-xl font-black text-gray-900 tracking-tight">
            全栈 Agent 智能交互工作台
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            FastAPI 异步 SSE 多通道管道 + Generative UI 动态响应组件
          </p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
          ● 状态机已就绪
        </span>
      </div>

      {/* 用户指令输入与触发按钮 */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          placeholder="请输入您希望 Agent 深入分析的任务指令..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
        />
        <button
          onClick={handleStartTask}
          disabled={isRunning}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-medium text-sm rounded-xl transition shadow-sm flex items-center gap-2 cursor-pointer"
        >
          {isRunning ? (
            <>
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Agent 正在深度推理...</span>
            </>
          ) : (
            '发起 Agent 任务'
          )}
        </button>
      </div>

      {/* 区域 1：思考链折叠展示 (Chain-of-Thought) */}
      {thoughts.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-gray-50 border border-gray-200/80 text-xs">
          <div className="font-bold text-gray-700 mb-2 flex items-center gap-1.5">
            <span>[思考链]</span> Agent 内部推理决策推导过程：
          </div>
          <div className="space-y-1 font-mono text-gray-600">
            {thoughts.map((th, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-indigo-500">[{th.stage}]</span>
                <span>{th.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 区域 2：外部工具调度进度日志 */}
      {toolLogs.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-blue-50/50 border border-blue-100 text-xs font-mono">
          <div className="font-bold text-blue-900 mb-1 flex items-center gap-1.5">
            <span>[工具调度]</span> 外部工具与微服务调用监控：
          </div>
          {toolLogs.map((log, i) => (
            <div key={i} className="text-blue-700 py-0.5">
              → 调度工具: <strong>{log.tool_name}</strong> | 状态: {log.status} {log.summary ? `(${log.summary})` : ''}
            </div>
          ))}
        </div>
      )}

      {/* 区域 3：【核心亮点】Generative UI 动态生成的富交互组件 */}
      {generativeCards.map((cardProps, index) => (
        <MetricDashboardCard key={index} {...cardProps} />
      ))}

      {/* 区域 4：实时打字机生成的文字建议 */}
      {streamedText && (
        <div className="mt-4 p-5 rounded-2xl bg-indigo-50/30 border border-indigo-100 text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">
          {streamedText}
        </div>
      )}
    </div>
  );
};
