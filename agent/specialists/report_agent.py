"""
Report Agent - 报告生成专家

职责：生成用户扫地机器人使用情况报告
工具：
    - get_user_id: 获取当前用户ID
    - get_current_month: 获取当前月份
    - fetch_external_data: 获取用户使用记录
    - rag_summarize: 检索产品知识（用于生成保养建议）
特点：严格遵循报告生成流程，输出结构化Markdown报告

架构位置：
    Supervisor → [Report Agent] → get_user_id + get_current_month + fetch_external_data + rag_summarize → 报告

工作流程：
    1. 接收用户的报告生成请求
    2. 调用get_user_id获取用户ID
    3. 调用get_current_month获取当前月份
    4. 调用fetch_external_data获取用户使用记录
    5. 可选调用rag_summarize获取保养建议
    6. 整合数据生成结构化Markdown报告
"""
from langchain.agents import create_agent
from model.factory import chat_model
from agent.tool.agent_tools import get_user_id, get_current_month, fetch_external_data, rag_summarize
from agent.tool.middleware import monitor_tool, log_before_model
from utils.logger_handler import logger
from utils.prompt_loader import load_report_prompt
# Token成本追踪 (#10)
from utils.token_callback import TokenTrackingCallbackHandler



class ReportAgent:
    """
    报告生成专家Agent

    专注于用户使用报告生成场景，配备4个工具：
    - get_user_id: 获取用户唯一标识
    - get_current_month: 获取当前月份
    - fetch_external_data: 获取用户使用记录数据
    - rag_summarize: 检索产品知识用于生成保养建议

    报告生成遵循固定流程：获取用户ID → 获取月份 → 获取使用数据 → 生成报告

    Attributes:
        system_prompt: 报告Agent的专属提示词（复用report_prompt.txt）
        agent: LangChain ReAct Agent实例，具备报告生成所需的全部工具
    """

    def __init__(self):
        # 报告Agent复用现有的report_prompt.txt
        self.system_prompt = load_report_prompt()
        # 创建ReAct Agent，配备报告生成所需的4个工具
        self.agent = create_agent(
            model=chat_model,
            system_prompt=self.system_prompt,
            tools=[get_user_id, get_current_month, fetch_external_data, rag_summarize],
            middleware=[monitor_tool, log_before_model]
        )

    def execute_stream(self, query: str):
        """
        流式执行报告Agent

        工作流程：
        1. 将用户问题构造为Agent输入
        2. Agent自主按流程调用工具获取数据
        3. 整合数据生成结构化Markdown报告
        4. 流式输出报告内容

        Args:
            query: 用户输入的报告生成请求

        Yields:
            str: 逐字符的回复内容片段
        """
        logger.info(f"[ReportAgent] 开始处理报告生成请求: {query[:80]}")
        input_dict = {
            "messages": [{"role": "user", "content": query}]
        }

        previous_content = ""
        try:
            # 传入Token追踪回调 (#10)
            callbacks = [TokenTrackingCallbackHandler(source="report")]
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
            logger.error(f"[ReportAgent] 执行失败: {e}")
            yield f"抱歉，报告生成过程中出现错误，请稍后再试。"
