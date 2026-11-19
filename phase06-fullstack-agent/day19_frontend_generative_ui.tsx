/**
 * DAY 19 实战源码：全栈 Agent 前端 —— 企业级“四大万能模板”动态渲染架构
 * ==============================================================================
 * 【企业级 Generative UI 终极设计哲学】：
 *   前端不按“具体业务工具”写死组件（否则 50 个工具要写 50 个组件），
 *   而是按“展示与交互形态”只抽象出【4 个万能动态模板组件】：
 *
 *   1. UniversalMetricCard  （万能指标/详情模板）：
 *      -> 通过 items.map() 动态渲染任意 N 个 {label, value} 格子 + 动态主题色。
 *      -> 同时通吃：【行业指标工具】+【实时天气工具】+ 股票/订单详情！
 *   2. UniversalCompareCard （万能双栏对照模板）：
 *      -> 动态渲染 原文 vs 译文/改写内容 + 核心词汇芯片 + 一键复制。
 *      -> 通吃：【多语种翻译工具】+ 代码重构对比 + 文案润色对比！
 *   3. UniversalTableCard   （万能动态表格模板）：
 *      -> 通过 columns.map() 和 rows.map() 动态渲染任意列数和行数的二维表格。
 *      -> 通吃：【技术框架对比表】+ 账单流水清单 + 数据库检索结果！
 *   4. UniversalConfirmCard （万能人机协同审批模板）：
 *      -> 动态渲染高危操作参数明细 + 风险等级警示 + 前端【批准执行 / 驳回】交互闭环。
 *      -> 通吃：【生产环境发布审批】+ 大额退款确认 + 群发邮件确认！
 * ==============================================================================
 */

import React, { useState, useEffect, useRef } from 'react';

// ==============================================================================
// 1. 四大万能模板的通用字段契约 (Universal Template Schemas)
// ==============================================================================

/**
 * 🌟【模板 1 契约】：UniversalMetricCard（万能指标/详情卡 —— 同时通吃行业指标、天气预报、股票、订单）
 */
interface UniversalMetricCardProps {
  title: string;
  badge: string;
  theme?: 'indigo' | 'sky' | 'emerald' | 'amber';
  // 核心：无论后端是什么业务工具，只要转成 { label, value, subtext } 数组，前端自动循环画格子！
  items: Array<{ label: string; value: string; subtext?: string }>;
  notice?: string;
  tags?: string[];
  action_label?: string;
  action_done_label?: string;
}

/**
 * 🌟【模板 2 契约】：UniversalCompareCard（万能双栏/上下对照卡 —— 通吃多语种翻译、代码重构对比、文案润色）
 */
interface UniversalCompareCardProps {
  title: string;
  badge: string;
  subtitle?: string;
  source_title: string;
  source_content: string;
  target_title: string;
  target_content: string;
  highlights?: string[];
}

/**
 * 🌟【模板 3 契约】：UniversalTableCard（万能动态表格卡 —— 通吃框架对比、账单流水、SQL 查询列表）
 */
interface UniversalTableCardProps {
  title: string;
  badge: string;
  columns: string[];   // 动态表头数组
  rows: string[][];    // 动态二维行数据数组
  summary?: string;    // 底部结论摘要
}

/**
 * 🌟【模板 4 契约】：UniversalConfirmCard（万能人机协同审批卡 —— 通吃生产发布审批、大额报销确认、删库确认）
 */
interface UniversalConfirmCardProps {
  approval_id?: string;
  title: string;
  badge: string;
  risk_level: 'low' | 'medium' | 'high';
  description: string;
  details: Array<{ label: string; value: string }>;
  command_or_action?: string;
  onDecision?: (approvalId: string, decision: 'approved' | 'rejected') => void;
}

interface GenerativeUIPayload {
  component_type: string;
  props: Record<string, any>;
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
// 2. 四大万能模板组件实现 (4 Universal Templates)
// ==============================================================================

/**
 * 🎨【万能模板 1】：UniversalMetricCard（1 个模板同时渲染“行业指标卡”与“天气预报卡”！）
 */
export const UniversalMetricCard: React.FC<UniversalMetricCardProps> = ({
  title,
  badge,
  theme = 'indigo',
  items = [],
  notice,
  tags = [],
  action_label = '+ 加入自选监控',
  action_done_label = '✓ 已订阅',
}) => {
  const [active, setActive] = useState(false);

  // 动态主题样式映射表
  const themeStyles = {
    indigo: {
      card: 'border-indigo-100 bg-gradient-to-br from-indigo-50/70 via-white to-blue-50/40',
      badge: 'bg-indigo-100 text-indigo-700',
      val: 'text-indigo-600',
      notice: 'bg-amber-50/80 text-amber-800 border-amber-200/60',
      btn: 'bg-indigo-600 hover:bg-indigo-700',
    },
    sky: {
      card: 'border-sky-100 bg-gradient-to-br from-sky-50/80 via-white to-cyan-50/50',
      badge: 'bg-sky-100 text-sky-700',
      val: 'text-sky-600',
      notice: 'bg-sky-50 text-sky-900 border-sky-200/60',
      btn: 'bg-sky-600 hover:bg-sky-700',
    },
    emerald: {
      card: 'border-emerald-100 bg-gradient-to-br from-emerald-50/70 via-white to-teal-50/40',
      badge: 'bg-emerald-100 text-emerald-700',
      val: 'text-emerald-600',
      notice: 'bg-emerald-50 text-emerald-900 border-emerald-200/60',
      btn: 'bg-emerald-600 hover:bg-emerald-700',
    },
    amber: {
      card: 'border-amber-100 bg-gradient-to-br from-amber-50/70 via-white to-orange-50/40',
      badge: 'bg-amber-100 text-amber-700',
      val: 'text-amber-600',
      notice: 'bg-amber-50 text-amber-900 border-amber-200/60',
      btn: 'bg-amber-600 hover:bg-amber-700',
    },
  }[theme];

  return (
    <div className={`my-4 p-5 rounded-2xl border shadow-sm transition-all hover:shadow-md ${themeStyles.card}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-gray-800">{title}</h3>
        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${themeStyles.badge}`}>
          {badge} · 模板1
        </span>
      </div>

      {/* 🌟 万能动态指标栅格：后端传 2 个就是 2 列，传 3 个（如天气温湿度风力）自动变 3 列！ */}
      <div className={`grid gap-3 mb-3 ${items.length >= 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
        {items.map((item, idx) => (
          <div key={idx} className="p-3 bg-white rounded-xl border border-gray-100 shadow-2xs">
            <div className="text-xs text-gray-500 mb-1">{item.label}</div>
            <div className={`text-2xl font-black font-mono ${themeStyles.val}`}>{item.value}</div>
            {item.subtext && <div className="text-xs text-gray-500 font-medium mt-0.5">{item.subtext}</div>}
          </div>
        ))}
      </div>

      {notice && (
        <div className={`text-xs p-2.5 rounded-lg border mb-3 ${themeStyles.notice}`}>
          {notice}
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <div className="flex gap-1.5 flex-wrap">
          {tags.map((t, idx) => (
            <span key={idx} className="text-[11px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded-md">
              #{t}
            </span>
          ))}
        </div>
        <button
          onClick={() => setActive(!active)}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium text-white transition cursor-pointer ${
            active ? 'bg-emerald-600' : themeStyles.btn
          }`}
        >
          {active ? action_done_label : action_label}
        </button>
      </div>
    </div>
  );
};

/**
 * 🎨【万能模板 2】：UniversalCompareCard（万能对照卡 —— 翻译、润色、代码对比通用）
 */
export const UniversalCompareCard: React.FC<UniversalCompareCardProps> = ({
  title,
  badge,
  subtitle,
  source_title,
  source_content,
  target_title,
  target_content,
  highlights = [],
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(target_content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-4 p-5 rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50/70 via-white to-teal-50/40 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-bold text-gray-800">{title}</h3>
          {subtitle && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-gray-100 text-gray-600">{subtitle}</span>
          )}
        </div>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">
          {badge} · 模板2
        </span>
      </div>

      <div className="space-y-2.5 mb-3">
        <div className="p-3 bg-white/80 rounded-xl border border-gray-100">
          <div className="text-[11px] text-gray-400 mb-1">{source_title}</div>
          <div className="text-xs text-gray-600 leading-relaxed">{source_content}</div>
        </div>
        <div className="p-3.5 bg-white rounded-xl border border-emerald-200/80 shadow-2xs">
          <div className="text-[11px] text-emerald-600 font-semibold mb-1">{target_title}</div>
          <div className="text-base font-bold text-gray-900 leading-relaxed">{target_content}</div>
        </div>
      </div>

      {highlights.length > 0 && (
        <div className="mb-3">
          <div className="text-[11px] font-semibold text-gray-500 mb-1.5">📚 核心词汇与要点解析：</div>
          <div className="flex gap-1.5 flex-wrap">
            {highlights.map((item, idx) => (
              <span
                key={idx}
                className="text-xs px-2.5 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200/60 rounded-lg font-mono"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <span className="text-[11px] text-gray-400">UniversalCompareCard 通用对照引擎</span>
        <button
          onClick={handleCopy}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium text-white transition cursor-pointer ${
            copied ? 'bg-gray-800' : 'bg-emerald-600 hover:bg-emerald-700'
          }`}
        >
          {copied ? '✓ 已复制到剪贴板' : '📋 一键复制结果'}
        </button>
      </div>
    </div>
  );
};

/**
 * 🎨【万能模板 3】：UniversalTableCard（万能动态表格卡 —— 任意列数、任意行数的二维数据对比）
 */
export const UniversalTableCard: React.FC<UniversalTableCardProps> = ({
  title,
  badge,
  columns = [],
  rows = [],
  summary,
}) => {
  const [selectedRow, setSelectedRow] = useState<number | null>(null);

  return (
    <div className="my-4 p-5 rounded-2xl border border-purple-100 bg-gradient-to-br from-purple-50/50 via-white to-indigo-50/30 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-gray-800">{title}</h3>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
          {badge} · 模板3
        </span>
      </div>

      {/* 🌟 动态表头与二维行循环渲染 */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white mb-3">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-gray-600 font-bold">
              {columns.map((col, idx) => (
                <th key={idx} className="py-2.5 px-3">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row, rIdx) => (
              <tr
                key={rIdx}
                onClick={() => setSelectedRow(rIdx === selectedRow ? null : rIdx)}
                className={`cursor-pointer transition ${
                  selectedRow === rIdx ? 'bg-purple-50 font-medium' : 'hover:bg-gray-50/80'
                }`}
              >
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="py-2.5 px-3 text-gray-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {summary && (
        <div className="text-xs text-purple-900 bg-purple-50/80 p-2.5 rounded-lg border border-purple-200/60">
          💡 <strong>[选型/数据洞察]</strong> {summary}
        </div>
      )}
    </div>
  );
};

/**
 * 🎨【万能模板 4】：UniversalConfirmCard（万能人机协同审批卡 —— 高危操作拦截确认）
 */
export const UniversalConfirmCard: React.FC<UniversalConfirmCardProps> = ({
  approval_id = '',
  title,
  badge,
  risk_level = 'high',
  description,
  details = [],
  command_or_action,
  onDecision,
}) => {
  const [status, setStatus] = useState<'pending' | 'approved' | 'rejected'>('pending');

  const handleClick = (decision: 'approved' | 'rejected') => {
    setStatus(decision);
    if (onDecision && approval_id) {
      onDecision(approval_id, decision);
    }
  };

  const riskBadge = {
    low: 'bg-blue-100 text-blue-700',
    medium: 'bg-amber-100 text-amber-800',
    high: 'bg-rose-100 text-rose-700',
  }[risk_level];

  return (
    <div className="my-4 p-5 rounded-2xl border-2 border-rose-200 bg-gradient-to-br from-rose-50/60 via-white to-amber-50/30 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-bold text-gray-900">{title}</h3>
          <span className={`text-[11px] px-2 py-0.5 rounded font-bold uppercase ${riskBadge}`}>
            风险等级: {risk_level}
          </span>
        </div>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-700 font-medium">
          {badge} · 模板4
        </span>
      </div>

      <p className="text-xs text-gray-600 mb-3">{description}</p>

      {/* 待审参数列表 */}
      <div className="bg-white rounded-xl border border-rose-100 p-3 mb-3 space-y-1.5">
        {details.map((d, idx) => (
          <div key={idx} className="flex justify-between text-xs border-b border-gray-50 pb-1 last:border-none last:pb-0">
            <span className="text-gray-500">{d.label}：</span>
            <span className="font-semibold text-gray-800">{d.value}</span>
          </div>
        ))}
        {command_or_action && (
          <div className="mt-2 pt-2 border-t border-gray-100 font-mono text-[11px] text-rose-700 bg-rose-50/60 p-2 rounded">
            待执行指令: $ {command_or_action}
          </div>
        )}
      </div>

      {/* 审批状态按钮交互区：点击后不仅改变卡片状态，还会通知后端恢复工作流继续走下一步！ */}
      <div className="flex items-center justify-between pt-2 border-t border-rose-100">
        <span className="text-[11px] font-mono text-gray-400">
          {approval_id ? `审批单号: ${approval_id}` : '人在回路安全边界'}
        </span>
        <div className="flex items-center gap-2.5">
          {status === 'pending' ? (
            <>
              <button
                onClick={() => handleClick('rejected')}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 transition cursor-pointer"
              >
                ✕ 驳回拦截 (通知后台中止)
              </button>
              <button
                onClick={() => handleClick('approved')}
                className="px-4 py-1.5 rounded-lg text-xs font-medium bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition cursor-pointer"
              >
                ✓ 批准并授权后台执行
              </button>
            </>
          ) : status === 'approved' ? (
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
              ✓ 已向后台发送【批准授权】，正在执行下一步流程...
            </span>
          ) : (
            <span className="text-xs font-bold text-rose-600 bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200">
              ✕ 已向后台发送【驳回指令】，操作已安全拦截！
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// ==============================================================================
// 3. 🌟【前端核心企业级架构】UI_COMPONENT_MAP —— 只注册这 4 个万能模板！
// ==============================================================================
// 以后后端哪怕扩展到 50 个业务工具，只要归类到这 4 种展示形态里，前端永远只需要这 4 行映射！

const UI_COMPONENT_MAP: Record<string, React.FC<any>> = {
  UniversalMetricCard: UniversalMetricCard,   // 模板 1：万能指标/详情卡（通吃行业研报、天气、股票、订单）
  UniversalCompareCard: UniversalCompareCard, // 模板 2：万能双栏对照卡（通吃翻译、代码重构、润色对比）
  UniversalTableCard: UniversalTableCard,     // 模板 3：万能动态表格卡（通吃框架对比、账单清单、SQL列表）
  UniversalConfirmCard: UniversalConfirmCard, // 模板 4：万能人机审批卡（通吃生产发布确认、退款审批）
};

// ==============================================================================
// 4. 主界面容器与多事件 SSE 消费逻辑 (Agent Terminal)
// ==============================================================================

export const AgentStreamingTerminal: React.FC = () => {
  const [userPrompt, setUserPrompt] = useState('分析 2026 年新能源汽车出海战略');
  const [isRunning, setIsRunning] = useState(false);

  const [thoughts, setThoughts] = useState<ThoughtEvent[]>([]);
  const [toolLogs, setToolLogs] = useState<ToolEvent[]>([]);
  const [generativeCards, setGenerativeCards] = useState<GenerativeUIPayload[]>([]);
  const [streamedText, setStreamedText] = useState('');

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleStartTask = (customPrompt?: string) => {
    if (isRunning) return;
    const targetPrompt = customPrompt ?? userPrompt;
    if (customPrompt) {
      setUserPrompt(customPrompt);
    }

    setIsRunning(true);
    setThoughts([]);
    setToolLogs([]);
    setGenerativeCards([]);
    setStreamedText('');

    const url = `http://127.0.0.1:8019/api/agent/stream?prompt=${encodeURIComponent(targetPrompt)}`;
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    sse.addEventListener('thought', (e: MessageEvent) => {
      const data: ThoughtEvent = JSON.parse(e.data);
      setThoughts((prev) => [...prev, data]);
    });

    sse.addEventListener('tool_call', (e: MessageEvent) => {
      const data: ToolEvent = JSON.parse(e.data);
      setToolLogs((prev) => [...prev, data]);
    });

    sse.addEventListener('generative_ui', (e: MessageEvent) => {
      const payload: GenerativeUIPayload = JSON.parse(e.data);
      setGenerativeCards((prev) => [...prev, payload]);
    });

    sse.addEventListener('message_chunk', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setStreamedText((prev) => prev + data.delta);
    });

    sse.addEventListener('done', () => {
      sse.close();
      setIsRunning(false);
    });

    sse.onerror = () => {
      sse.close();
      setIsRunning(false);
    };
  };

  /**
   * 🌟【第二阶段：人机协同恢复】
   * 当用户在 UniversalConfirmCard 卡片上点击【批准】或【驳回】时，
   * 携带 approval_id 和 decision ('approved' | 'rejected') 唤醒后端继续走下一步流程！
   */
  const handleApprovalDecision = (approvalId: string, decision: 'approved' | 'rejected') => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsRunning(true);
    setStreamedText('');

    const url = `http://127.0.0.1:8019/api/agent/approval/stream?approval_id=${encodeURIComponent(
      approvalId
    )}&decision=${decision}`;
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    sse.addEventListener('thought', (e: MessageEvent) => {
      const data: ThoughtEvent = JSON.parse(e.data);
      setThoughts((prev) => [...prev, data]);
    });

    sse.addEventListener('tool_call', (e: MessageEvent) => {
      const data: ToolEvent = JSON.parse(e.data);
      setToolLogs((prev) => [...prev, data]);
    });

    sse.addEventListener('message_chunk', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setStreamedText((prev) => prev + data.delta);
    });

    sse.addEventListener('done', () => {
      sse.close();
      setIsRunning(false);
    });

    sse.onerror = () => {
      sse.close();
      setIsRunning(false);
    };
  };

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
      <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-5">
        <div>
          <h2 className="text-xl font-black text-gray-900 tracking-tight">
            全栈 Agent 工作台 (企业级“四大万能模板”架构)
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            5 大后端业务工具 ➔ 自动归一映射到前端 4 套通用视觉模板组件
          </p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
          ● 4 大万能模板已就绪
        </span>
      </div>

      {/* 快捷体验按钮区：5 个不同业务场景 -> 验证 4 大万能模板 */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-xs text-gray-400">一键测试 5 大工具 ➔ 4 大模板：</span>
        <button
          disabled={isRunning}
          onClick={() => handleStartTask('分析 2026 年新能源汽车出海战略')}
          className="text-xs px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium transition cursor-pointer disabled:opacity-50"
        >
          📊 行业指标 (走模板1)
        </button>
        <button
          disabled={isRunning}
          onClick={() => handleStartTask('深圳今天天气怎么样？出门穿什么衣服合适？')}
          className="text-xs px-2.5 py-1 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 font-medium transition cursor-pointer disabled:opacity-50"
        >
          🌤️ 城市天气 (共用模板1!)
        </button>
        <button
          disabled={isRunning}
          onClick={() =>
            handleStartTask('请把“前端工程师转型 AI Agent 开发具有天然的全栈交互与状态机优势”翻译成地道英文')
          }
          className="text-xs px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-medium transition cursor-pointer disabled:opacity-50"
        >
          🌐 多语种翻译 (走模板2)
        </button>
        <button
          disabled={isRunning}
          onClick={() =>
            handleStartTask('请用表格对比 LangGraph、AutoGen、CrewAI 三大主流 Agent 框架的核心优势与适用场景')
          }
          className="text-xs px-2.5 py-1 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium transition cursor-pointer disabled:opacity-50"
        >
          📋 框架对比表 (走模板3)
        </button>
        <button
          disabled={isRunning}
          onClick={() =>
            handleStartTask('请帮我将 agent-web-portal 项目发布上线到 prod 生产环境，镜像版本 v2.4.0')
          }
          className="text-xs px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 font-medium transition cursor-pointer disabled:opacity-50"
        >
          🛡️ 高危发布审批 (走模板4)
        </button>
      </div>

      {/* 输入与提交 */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          placeholder="输入指标分析、天气、翻译、表格对比、或高危发布审批指令..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
        />
        <button
          onClick={() => handleStartTask()}
          disabled={isRunning}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-medium text-sm rounded-xl transition shadow-sm flex items-center gap-2 cursor-pointer"
        >
          {isRunning ? 'Agent 推理中...' : '发起 Agent 任务'}
        </button>
      </div>

      {/* 区域 1：思考链阶段日志 */}
      {thoughts.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-gray-50 border border-gray-200/80 text-xs">
          <div className="font-bold text-gray-700 mb-2">[执行进度] Agent 当前处理阶段：</div>
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

      {/* 区域 2：工具调度日志 */}
      {toolLogs.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-blue-50/50 border border-blue-100 text-xs font-mono">
          <div className="font-bold text-blue-900 mb-1">[工具调度] 后端工具 ➔ 前端万能模板映射监控：</div>
          {toolLogs.map((log, i) => (
            <div key={i} className="text-blue-700 py-0.5">
              → 调度工具: <strong>{log.tool_name}</strong> | 状态: {log.status} {log.summary ? `(${log.summary})` : ''}
            </div>
          ))}
        </div>
      )}

      {/* 区域 3：🌟【四大万能模板动态挂载区】查 UI_COMPONENT_MAP 渲染，并注入 onDecision 回调支持人机审批闭环 */}
      {generativeCards.map((card, index) => {
        const TargetTemplate = UI_COMPONENT_MAP[card.component_type];
        if (!TargetTemplate) {
          return (
            <div key={index} className="p-3 text-xs text-red-600 bg-red-50 rounded-lg">
              未注册的万能模板类型: {card.component_type}
            </div>
          );
        }
        return <TargetTemplate key={index} {...card.props} onDecision={handleApprovalDecision} />;
      })}

      {/* 区域 4：流式打字机总结 */}
      {streamedText && (
        <div className="mt-4 p-5 rounded-2xl bg-indigo-50/30 border border-indigo-100 text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">
          {streamedText}
        </div>
      )}
    </div>
  );
};
