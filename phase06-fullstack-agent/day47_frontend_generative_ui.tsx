/**
 * DAY 47 实战源码：全栈 Agent 前端 —— 流式消费与 Generative UI 动态组件渲染
 * 文件说明：
 *   传统的前端 AI 聊天只负责把文本一行行打出来。
 *   高级 Agent 工程师的核心技能是：能够监听后端的自定义 SSE 事件，
 *   把工具调用状态渲染为折叠面板，把结构化数据动态渲染为交互卡片（Generative UI）！
 * 技术栈：React 18/19 + TypeScript + Tailwind CSS
 */

import React, { useState, useEffect, useRef } from 'react';

// ==============================================================================
// 1. 类型定义（对应后端下发的事件契约）
// ==============================================================================

interface MetricCardProps {
  title: string;
  penetration_rate: string;
  export_growth: string;
  risk_warning: string;
  tags: string[];
}

interface ThoughtEvent {
  stage: string;
  message: string;
}

interface ToolEvent {
  tool_name: string;
  status: 'executing' | 'completed';
  summary?: string;
}

// ==============================================================================
// 2. 动态生成的 UI 卡片组件 (Generative UI Component)
// ==============================================================================

export const MetricDashboardCard: React.FC<MetricCardProps> = ({
  title,
  penetration_rate,
  export_growth,
  risk_warning,
  tags,
}) => {
  const [isFollowed, setIsFollowed] = useState(false);

  return (
    <div className="my-4 p-5 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></span>
          {title}
        </h3>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">
          AI 动态组件
        </span>
      </div>

      {/* 关键数据指标栅格 */}
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
        ⚠️ <strong>风险关注：</strong> {risk_warning}
      </div>

      {/* 标签与操作按钮 */}
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
          className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
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
// 3. 主界面容器与多事件 SSE 消费逻辑
// ==============================================================================

export const AgentStreamingTerminal: React.FC = () => {
  const [userPrompt, setUserPrompt] = useState('分析 2026 年新能源汽车出海战略');
  const [isRunning, setIsRunning] = useState(false);
  const [thoughts, setThoughts] = useState<ThoughtEvent[]>([]);
  const [toolLogs, setToolLogs] = useState<ToolEvent[]>([]);
  const [generativeCards, setGenerativeCards] = useState<MetricCardProps[]>([]);
  const [streamedText, setStreamedText] = useState('');

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleStartTask = () => {
    if (isRunning) return;

    // 清空历史状态
    setIsRunning(true);
    setThoughts([]);
    setToolLogs([]);
    setGenerativeCards([]);
    setStreamedText('');

    // 建立标准 SSE 连接
    const url = `http://127.0.0.1:8000/api/agent/stream?prompt=${encodeURIComponent(userPrompt)}`;
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    // 1. 监听思考事件
    sse.addEventListener('thought', (e: MessageEvent) => {
      const data: ThoughtEvent = JSON.parse(e.data);
      setThoughts((prev) => [...prev, data]);
    });

    // 2. 监听工具调度事件
    sse.addEventListener('tool_call', (e: MessageEvent) => {
      const data: ToolEvent = JSON.parse(e.data);
      setToolLogs((prev) => [...prev, data]);
    });

    // 3. 核心：监听 Generative UI 事件，将数据挂载到组件渲染列表
    sse.addEventListener('generative_ui', (e: MessageEvent) => {
      const payload = JSON.parse(e.data);
      if (payload.component_type === 'MetricDashboardCard') {
        setGenerativeCards((prev) => [...prev, payload.props]);
      }
    });

    // 4. 监听文本打字机流
    sse.addEventListener('message_chunk', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setStreamedText((prev) => prev + data.delta);
    });

    // 5. 监听完成信号
    sse.addEventListener('done', () => {
      console.log('Agent 执行流程结束');
      sse.close();
      setIsRunning(false);
    });

    sse.onerror = (err) => {
      console.error('SSE 通信发生异常:', err);
      sse.close();
      setIsRunning(false);
    };
  };

  useEffect(() => {
    return () => {
      // 组件卸载时切断未完成的长连接
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="max-w-3xl mx-auto my-8 p-6 bg-white rounded-3xl shadow-xl border border-gray-100 font-sans">
      <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
        <div>
          <h2 className="text-xl font-black text-gray-900 tracking-tight">
            全栈 Agent 交互工作台
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            基于 FastAPI 异步 SSE 管道 + Generative UI 动态交互
          </p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
          ● 状态机已连接
        </span>
      </div>

      {/* 输入与调度区 */}
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
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-medium text-sm rounded-xl transition shadow-sm flex items-center gap-2"
        >
          {isRunning ? (
            <>
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>推理调度中...</span>
            </>
          ) : (
            '发起 Agent 任务'
          )}
        </button>
      </div>

      {/* 思考链过程折叠卡片 */}
      {thoughts.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-gray-50 border border-gray-200/80 text-xs">
          <div className="font-bold text-gray-700 mb-2 flex items-center gap-1.5">
            <span>🧠</span> Agent 推理思考链路 (Chain-of-Thought)
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

      {/* 外部工具执行进度 */}
      {toolLogs.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-blue-50/50 border border-blue-100 text-xs font-mono">
          <div className="font-bold text-blue-900 mb-1 flex items-center gap-1.5">
            <span>⚡</span> 外部工具调用日志 (Tool Executions)
          </div>
          {toolLogs.map((log, i) => (
            <div key={i} className="text-blue-700 py-0.5">
              → 调度工具: <strong>{log.tool_name}</strong> | 状态: {log.status} {log.summary ? `(${log.summary})` : ''}
            </div>
          ))}
        </div>
      )}

      {/* Generative UI 核心：根据后端数据动态渲染的高级组件 */}
      {generativeCards.map((cardProps, index) => (
        <MetricDashboardCard key={index} {...cardProps} />
      ))}

      {/* 实时打字机生成的文字建议 */}
      {streamedText && (
        <div className="mt-4 p-5 rounded-2xl bg-indigo-50/30 border border-indigo-100 text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">
          {streamedText}
        </div>
      )}
    </div>
  );
};
