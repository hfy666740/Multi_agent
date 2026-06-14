"""
Weather Agent - 天气顾问

职责：查询天气信息，提供天气详情和出行建议
工具：get_weather（查询城市天气）、get_user_location（获取用户所在城市）
特点：
    - 默认只回复天气信息，不主动提及扫地机器人
    - 只有用户明确问到天气对扫地机器人的影响时才给相关建议

架构位置：
    Supervisor → [Weather Agent] → get_user_location + get_weather → 天气回答

工作流程：
    1. 接收用户的天气相关问题
    2. 如未指定城市，先调用get_user_location获取用户位置
    3. 调用get_weather查询天气信息
    4. 结构化输出天气详情（气温、湿度、风向、出门建议等）
    5. 仅在用户明确要求时给出扫地机器人相关建议
"""
from langchain.agents import create_agent
from model.factory import chat_model
from agent.tool.agent_tools import get_weather, get_user_location
from agent.tool.middleware import monitor_tool, log_before_model
from utils.logger_handler import logger
# 统一通过prompt_loader加载提示词 (#4)
from utils.prompt_loader import weather_load_prompt
# Token成本追踪 (#10)
from utils.token_callback import TokenTrackingCallbackHandler


class WeatherAgent:
    """
    天气顾问Agent

    专注于天气查询场景，配备get_weather和get_user_location两个工具。
    核心设计原则：问天气只报天气，不主动提扫地机器人。

    Attributes:
        system_prompt: 天气Agent的专属提示词，包含天气查询规则和机器人建议规则（通过prompt_loader统一加载）
        agent: LangChain ReAct Agent实例，具备天气查询和定位工具
    """

    def __init__(self):
        # 通过统一提示词加载器获取提示词 (#4)
        self.system_prompt = weather_load_prompt()
        # 创建ReAct Agent，配备天气查询和定位工具
        self.agent = create_agent(
            model=chat_model,
            system_prompt=self.system_prompt,
            tools=[get_weather, get_user_location],
            middleware=[monitor_tool, log_before_model]
        )

    def execute_stream(self, query: str):
        """
        流式执行天气Agent

        工作流程：
        1. 将用户问题构造为Agent输入
        2. Agent自主决定是否需要先获取用户位置
        3. Agent调用get_weather查询天气
        4. 流式输出天气信息

        Args:
            query: 用户输入的天气相关问题

        Yields:
            str: 逐字符的回复内容片段
        """
        logger.info(f"[WeatherAgent] 开始处理天气查询问题: {query[:80]}")
        input_dict = {
            "messages": [{"role": "user", "content": query}]
        }

        previous_content = ""
        try:
            # 传入Token追踪回调 (#10)
            callbacks = [TokenTrackingCallbackHandler(source="weather")]
            for chunk in self.agent.stream(
                input_dict, stream_mode="values",
                context={"report": False},
                config={"callbacks": callbacks}
            ):
                latest_message = chunk["messages"][-1]
                if latest_message.content:
                    current_content = latest_message.content.strip()
                    new_content = current_content[len(previous_content):]
                    previous_content = current_content
                    if new_content:
                        yield new_content
        except Exception as e:
            logger.error(f"[WeatherAgent] 执行失败: {e}")
            yield f"抱歉，天气查询过程中出现错误，请稍后再试。"
