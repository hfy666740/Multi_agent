# test_supervisor.py — Supervisor Agent 意图分类单元测试
# 技术栈: pytest (测试框架), unittest.mock (LLM 模拟), LangChain (Agent 框架)

import pytest
from unittest.mock import MagicMock, patch


class TestSupervisorAgent:
    """Supervisor Agent 意图分类单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("agent.supervisor.chat_model") as mock_llm, \
             patch("agent.supervisor.supervisor_load_prompt") as mock_prompt:
            mock_prompt.return_value = "你是一个意图分类器..."
            self.mock_llm = mock_llm
            self.mock_llm.invoke.return_value.content = "knowledge"
            from agent.supervisor import SupervisorAgent
            self.agent = SupervisorAgent()
            yield

    def test_route_knowledge(self):
        route = self.agent.route("扫地机器人怎么充电？")
        assert route == "knowledge"

    def test_route_weather(self):
        self.mock_llm.invoke.return_value.content = "weather"
        route = self.agent.route("今天天气怎么样？")
        assert route == "weather"

    def test_route_report(self):
        self.mock_llm.invoke.return_value.content = "report"
        route = self.agent.route("帮我生成使用报告")
        assert route == "report"

    def test_route_direct(self):
        self.mock_llm.invoke.return_value.content = "direct"
        route = self.agent.route("你好")
        assert route == "direct"

    def test_route_invalid_fallback(self):
        self.mock_llm.invoke.return_value.content = "invalid_route_xxx"
        route = self.agent.route("随便问问")
        assert route == "direct"

    def test_route_llm_error_fallback(self):
        self.mock_llm.invoke.side_effect = Exception("API Error")
        route = self.agent.route("会触发错误的问题")
        assert route == "direct"

    def test_direct_response_success(self):
        self.mock_llm.invoke.return_value.content = "你好！有什么可以帮你的？"
        response = self.agent.direct_response("你好")
        assert "你好" in response

    def test_direct_response_error(self):
        self.mock_llm.invoke.side_effect = Exception("API Error")
        response = self.agent.direct_response("你好")
        assert "抱歉" in response or "无法回答" in response
