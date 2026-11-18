"""Day 19 / 23｜验证天气输入不会误触发报告生成。"""

from fastapi.testclient import TestClient

import day19_backend_sse_stream as backend


def test_weather_request_does_not_generate_industry_report(monkeypatch):
    class UnexpectedModel:
        @property
        def chat(self):
            raise AssertionError("没有天气工具时不应调用报告模型")

    monkeypatch.setattr(backend, "async_client", UnexpectedModel())
    with TestClient(backend.app) as client:
        response = client.get("/api/agent/stream", params={"prompt": "今天深圳天气"})
    assert response.status_code == 200
    assert "尚未接入实时天气数据" in response.text
    assert "event: generative_ui" not in response.text
    assert "event: tool_call" not in response.text
    assert "event: done" in response.text
