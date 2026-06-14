# test_workflow.py — 多Agent协作工作流单元测试
# 技术栈: pytest (测试框架), unittest.mock (Agent 模拟), LangChain (Agent 框架)

import pytest
from unittest.mock import MagicMock, patch


class TestMultiAgentWorkflow:
    """多Agent工作流编排器单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("agent.workflow.SupervisorAgent") as mock_supervisor, \
             patch("agent.workflow.KnowledgeAgent") as mock_knowledge, \
             patch("agent.workflow.WeatherAgent") as mock_weather, \
             patch("agent.workflow.ReportAgent") as mock_report:
            self.mock_supervisor = MagicMock()
            mock_supervisor.return_value = self.mock_supervisor
            self.mock_knowledge = MagicMock()
            mock_knowledge.return_value = self.mock_knowledge
            self.mock_weather = MagicMock()
            mock_weather.return_value = self.mock_weather
            self.mock_report = MagicMock()
            mock_report.return_value = self.mock_report
            from agent.workflow import MultiAgentWorkflow
            self.workflow = MultiAgentWorkflow()
            yield

    def test_execute_stream_knowledge_route(self):
        self.mock_supervisor.route.return_value = "knowledge"
        self.mock_knowledge.execute_stream.return_value = iter(["扫地", "机器人", "知识回答"])
        result = list(self.workflow.execute_stream("扫地机器人怎么用？"))
        assert len(result) > 0
        self.mock_knowledge.execute_stream.assert_called_once()

    def test_execute_stream_weather_route(self):
        self.mock_supervisor.route.return_value = "weather"
        self.mock_weather.execute_stream.return_value = iter(["今天", "天气", "很好"])
        result = list(self.workflow.execute_stream("今天天气如何？"))
        assert "很好" in result[-1]
        self.mock_weather.execute_stream.assert_called_once()

    def test_execute_stream_report_route(self):
        self.mock_supervisor.route.return_value = "report"
        self.mock_report.execute_stream.return_value = iter(["使用", "报告", "已生成"])
        result = list(self.workflow.execute_stream("生成使用报告"))
        assert "已生成" in result[-1]
        self.mock_report.execute_stream.assert_called_once()

    def test_execute_stream_direct_route(self):
        self.mock_supervisor.route.return_value = "direct"
        self.mock_supervisor.direct_response.return_value = "你好！有什么需要帮助的？"
        result = list(self.workflow.execute_stream("你好"))
        assert "你好" in result[0]

    def test_execute_stream_unknown_route(self):
        self.mock_supervisor.route.return_value = "unknown_route"
        self.mock_supervisor.direct_response.return_value = "兜底回复"
        result = list(self.workflow.execute_stream("未知类型问题"))
        assert "兜底回复" in result[0]

    def test_chat_non_streaming(self):
        self.mock_supervisor.route.return_value = "direct"
        self.mock_supervisor.direct_response.return_value = "完整回复内容"
        result = self.workflow.chat("测试")
        assert result == "完整回复内容"
