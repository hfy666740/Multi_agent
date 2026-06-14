"""
多Agent协作工作流编排器

架构设计：Supervisor + 3个Specialist Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    用户提问
        │
        ▼
    ┌──────────────────────────┐
    │   Supervisor Agent       │  ← 意图识别 + 路由分发（LLM分类）
    │   (轻量级，不调用工具)     │
    └──────┬───────────────────┘
           │
           ├──→ 🤖 Knowledge Agent    (产品知识专家)
           │       工具: rag_summarize
           │       场景: 扫地机器人使用/故障/保养/选购
           │
           ├──→ 🌤️ Weather Agent      (天气顾问)
           │       工具: get_weather, get_user_location
           │       场景: 天气查询/出行建议
           │
           ├──→ 📊 Report Agent       (报告生成专家)
           │       工具: get_user_id, get_current_month,
           │             fetch_external_data, rag_summarize
           │       场景: 使用报告/数据统计
           │
           └──→ 💬 Supervisor直接回复  (闲聊/通用问题)

设计优势：
    1. 职责分离：每个Agent专注一个领域，提示词精简，回答更专业
    2. 工具隔离：每个Agent只配备相关工具，避免误调用
    3. 性能优化：Supervisor轻量级分类，闲聊无需路由到子Agent
    4. 易于扩展：新增场景只需添加新的Specialist Agent
    5. 独立提示词：每个Agent有专属提示词，互不干扰
"""

from agent.supervisor import SupervisorAgent
from agent.specialists.knowledge_agent import KnowledgeAgent
from agent.specialists.weather_agent import WeatherAgent
from agent.specialists.report_agent import ReportAgent
from utils.logger_handler import logger


class MultiAgentWorkflow:
    """
    多Agent协作工作流编排器

    负责协调Supervisor和各Specialist Agent之间的交互，
    提供统一的流式输出接口供API层调用。

    工作流程：
        1. 用户提问 → Supervisor分类意图（LLM路由）
        2. Supervisor路由到对应Specialist Agent
        3. Specialist Agent处理并流式返回结果
        4. 结果通过SSE流式返回给前端

    Attributes:
        supervisor: SupervisorAgent实例，负责意图分类和路由
        specialists: dict，键为路由名称，值为对应的Specialist Agent实例
    """

    def __init__(self):
        # 初始化Supervisor（意图分类器）
        self.supervisor = SupervisorAgent()

        # 初始化各Specialist Agent
        # 每个Agent独立初始化，配备专属工具和提示词
        self.specialists = {
            "knowledge": KnowledgeAgent(),   # 产品知识专家
            "weather": WeatherAgent(),       # 天气顾问
            "report": ReportAgent()          # 报告生成专家
        }

        logger.info("[MultiAgentWorkflow] 多Agent协作系统初始化完成")

    def execute_stream(self, query: str):
        """
        流式执行多Agent工作流

        完整工作流程：
        ┌─────────────────────────────────────────────────────┐
        │ Step 1: Supervisor意图分类                           │
        │   - 使用LLM对用户问题进行意图分类                      │
        │   - 返回路由目标: knowledge/weather/report/direct    │
        ├─────────────────────────────────────────────────────┤
        │ Step 2: 路由到对应Specialist Agent                   │
        │   - knowledge → KnowledgeAgent (RAG知识检索)         │
        │   - weather   → WeatherAgent   (天气查询)            │
        │   - report    → ReportAgent    (报告生成)            │
        │   - direct    → Supervisor直接回复 (闲聊)            │
        ├─────────────────────────────────────────────────────┤
        │ Step 3: Specialist流式输出                           │
        │   - Agent自主调用工具获取数据                         │
        │   - 逐字符流式输出回复内容                            │
        └─────────────────────────────────────────────────────┘

        Args:
            query: 用户输入的问题文本

        Yields:
            str: 逐字符的回复内容片段
        """
        # Step 1: Supervisor意图分类
        route = self.supervisor.route(query)
        logger.info(f"[MultiAgentWorkflow] 路由决策: {route}，用户问题: {query[:50]}")

        # Step 2 & 3: 根据路由决策执行对应Agent
        if route == "direct":
            # 通用问题，Supervisor直接回复
            logger.info(f"[Agent执行] 开始执行 Supervisor (直接回复) | 问题: {query[:80]}")
            response = self.supervisor.direct_response(query)
            logger.info(f"[Agent执行] Supervisor 执行完成 | 回复长度: {len(response)} 字符")
            yield response

        elif route in self.specialists:
            # 路由到对应的Specialist Agent
            agent = self.specialists[route]
            agent_display_names = {
                "knowledge": "Knowledge Agent (产品知识专家)",
                "weather": "Weather Agent (天气顾问)",
                "report": "Report Agent (报告生成专家)"
            }
            display_name = agent_display_names.get(route, route)
            logger.info(f"[Agent执行] 开始执行 {display_name} | 问题: {query[:80]}")
            for chunk in agent.execute_stream(query):
                yield chunk
            logger.info(f"[Agent执行] {display_name} 执行完成")

        else:
            # 未知路由，安全兜底
            logger.warning(f"[MultiAgentWorkflow] 未知路由: {route}，使用direct模式")
            response = self.supervisor.direct_response(query)
            yield response

    def chat(self, query: str) -> str:
        """
        非流式执行多Agent工作流

        与execute_stream相同的工作流程，但返回完整回复而非流式输出。
        适用于不需要流式响应的场景（如API测试、批量处理等）。

        Args:
            query: 用户输入的问题文本

        Returns:
            完整的回复文本
        """
        full_response = ""
        for chunk in self.execute_stream(query):
            full_response += chunk
        return full_response
