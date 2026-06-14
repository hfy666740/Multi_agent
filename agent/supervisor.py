"""
Supervisor Agent - 意图识别与路由分发

职责：接收用户问题，使用LLM判断意图，决定路由到哪个Specialist Agent处理。
设计原则：轻量级，不调用工具，仅做意图分类，减少Token消耗和响应延迟。

架构位置：
    用户提问 → [Supervisor] → knowledge / weather / report / direct

路由说明：
    - knowledge: 扫地机器人产品知识问题 → Knowledge Agent
    - weather:   天气查询相关问题       → Weather Agent
    - report:    使用报告生成请求       → Report Agent
    - direct:    通用闲聊/其他问题      → Supervisor直接回复
"""
from model.factory import chat_model
from utils.logger_handler import logger
# 统一通过prompt_loader加载提示词 (#4)
from utils.prompt_loader import supervisor_load_prompt
# Token成本追踪 (#10)
from utils.token_callback import TokenTrackingCallbackHandler
from utils.token_tracker import get_token_tracker
from langchain_core.messages import SystemMessage, HumanMessage

# 意图分类的合法路由列表
VALID_ROUTES = ["knowledge", "weather", "report", "direct"]


class SupervisorAgent:
    """
    Supervisor Agent - 意图分类器

    使用LLM对用户问题进行意图分类，决定路由到哪个Specialist Agent处理。
    对于"direct"类型的通用问题（闲聊、问候等），Supervisor直接生成回复，
    无需路由到子Agent，减少不必要的LLM调用。

    Attributes:
        model: LangChain ChatModel实例，用于意图分类和直接回复
        system_prompt: Supervisor的意图分类提示词（通过prompt_loader统一加载）
    """

    def __init__(self):
        self.model = chat_model
        self.system_prompt = supervisor_load_prompt()

    def route(self, query: str) -> str:
        """
        对用户问题进行意图分类，返回路由目标

        工作流程：
        1. 将用户问题与系统提示词组合为LLM输入
        2. LLM输出分类结果（knowledge/weather/report/direct）
        3. 验证分类结果是否合法，不合法则默认路由到direct

        Args:
            query: 用户输入的问题文本

        Returns:
            路由目标字符串，值为 "knowledge" | "weather" | "report" | "direct"
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=query)
        ]

        try:
            # 调用LLM进行意图分类，传入Token追踪回调 (#10)
            response = self.model.invoke(
                messages,
                config={"callbacks": [TokenTrackingCallbackHandler(source="supervisor")]}
            )
            route = response.content.strip().lower()

            # 验证路由结果是否合法
            if route not in VALID_ROUTES:
                logger.warning(f"[Supervisor] 意图分类结果不合法: {route}，默认路由到direct")
                route = "direct"

            logger.info(f"[Supervisor] 意图分类结果: {route}，用户问题: {query[:50]}")
            # 根据路由结果打印不同的Agent切换日志
            agent_names = {
                "knowledge": "Knowledge Agent (产品知识专家)",
                "weather": "Weather Agent (天气顾问)",
                "report": "Report Agent (报告生成专家)",
                "direct": "Supervisor (直接回复)"
            }
            agent_name = agent_names.get(route, route)
            logger.info(f"[Agent切换] Supervisor -> {agent_name} | 用户问题: {query[:80]}")
            return route

        except Exception as e:
            logger.error(f"[Supervisor] 意图分类失败: {e}，默认路由到direct")
            logger.info(f"[Agent切换] Supervisor -> Supervisor (直接回复-兜底) | 分类失败，使用默认路由")
            return "direct"

    def direct_response(self, query: str) -> str:
        """
        对direct类型的通用问题直接生成回复

        当Supervisor判断用户问题属于通用闲聊（如问候、感谢、
        通用知识等）时，直接生成回复，无需路由到子Agent，
        减少响应延迟和Token消耗。

        Args:
            query: 用户输入的问题文本

        Returns:
            LLM生成的回复文本
        """
        messages = [
            SystemMessage(
                content="你是智扫通智能客服，友好地回答用户的通用问题。保持简洁、友好。"
                        "如果用户的问题涉及扫地机器人、天气或报告，建议他们详细描述需求。"
            ),
            HumanMessage(content=query)
        ]

        try:
            response = self.model.invoke(
                messages,
                config={"callbacks": [TokenTrackingCallbackHandler(source="direct")]}
            )
            return response.content
        except Exception as e:
            logger.error(f"[Supervisor] 直接回复失败: {e}")
            return "抱歉，我暂时无法回答您的问题，请稍后再试。"
