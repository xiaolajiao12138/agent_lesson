"""Day 19 / 23｜验证企业级 5 大业务工具 -> 4 大万能前端模板 (UI_TOOL_MAP) 的归一化映射。"""

import day19_backend_sse_stream as backend


def test_five_tools_map_to_four_universal_templates():
    """验证行业指标与天气工具共用 UniversalMetricCard，其余工具映射至对应万能模板"""
    # 1. 行业指标 + 2. 天气工具 -> 共用模板 1：UniversalMetricCard
    assert backend.UI_TOOL_MAP["render_metric_dashboard"]["component_type"] == "UniversalMetricCard"
    assert backend.UI_TOOL_MAP["get_weather"]["component_type"] == "UniversalMetricCard"

    # 3. 翻译工具 -> 映射模板 2：UniversalCompareCard
    assert backend.UI_TOOL_MAP["translate_text"]["component_type"] == "UniversalCompareCard"

    # 4. 表格工具 -> 映射模板 3：UniversalTableCard
    assert backend.UI_TOOL_MAP["render_data_table"]["component_type"] == "UniversalTableCard"

    # 5. 审批工具 -> 映射模板 4：UniversalConfirmCard
    assert backend.UI_TOOL_MAP["request_action_approval"]["component_type"] == "UniversalConfirmCard"
