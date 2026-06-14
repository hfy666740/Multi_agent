"""
Knowledge Agent - 产品知识专家

职责：回答用户关于扫地/扫拖机器人的专业问题
工具：rag_summarize（从向量知识库检索参考资料）
特点：专注于产品知识领域，回答基于RAG检索结果，不编造信息

架构位置：
    Supervisor → [Knowledge Agent] → rag_summarize工具 → 向量知识库 → 专业回答

工作流程：
    1. 接收用户的产品知识问题
    2. 调用rag_summarize工具从向量知识库检索相关资料
    3. 基于检索结果，生成专业、准确的回答
    4. 流式输出回答内容
"""
from langchain.agents import create_agent
from model.factory import chat_model
from agent.tool.agent_tools import rag_summarize
from agent.tool.middleware import monitor_tool, log_before_model
from utils.logger_handler import logger
# 统一通过prompt_loader加载提示词 (#4)
from utils.prompt_loader import knowledge_load_prompt
# Token成本追踪 (#10)
from utils.token_callback import TokenTrackingCallbackHandler


class KnowledgeAgent:
    """
    产品知识专家Agent

    使用RAG（检索增强生成）技术从向量知识库中检索相关资料，
    生成专业、准确的产品知识回答。仅配备rag_summarize工具，
    确保回答基于知识库中的真实数据，不编造信息。

    Attributes:
        system_prompt: 知识Agent的专属提示词，指导其专注于产品知识领域
        agent: LangChain ReAct Agent实例，具备rag_summarize工具调用能力
    """

    def __init__(self):
        self.system_prompt = self._load_prompt()
        # 创建ReAct Agent，仅配备rag_summarize工具
        # 中间件：monitor_tool记录工具调用日志，log_before_model记录模型调用前状态
        self.agent = create_agent(
            model=chat_model,
            system_prompt=self.system_prompt,
            tools=[rag_summarize],
            middleware=[monitor_tool, log_before_model]
        )

    def _load_prompt(self) -> str:
        """
        加载知识Agent的专属提示词

        从prompt/knowledge_prompt.txt加载，该提示词指导Agent：
        - 专注于扫地机器人产品知识领域
        - 基于RAG检索结果回答，不编造信息
        - 给出具体、实用的建议

        Returns:
            提示词文本字符串
        """
        try:
            return knowledge_load_prompt()
        except Exception as e:
            logger.error(f"[KnowledgeAgent] 加载提示词失败: {e}")
            raise e

    def execute_stream(self, query: str):
        """
        流式执行知识Agent

        工作流程：
        1. 将用户问题构造为Agent输入
        2. Agent自主决定是否调用rag_summarize工具
        3. 流式输出Agent的回复内容（逐字符）

        Args:
            query: 用户输入的产品知识问题

        Yields:
            str: 逐字符的回复内容片段
        """
        logger.info(f"[KnowledgeAgent] 开始处理产品知识问题: {query[:80]}")
        input_dict = {
            "messages": [{"role": "user", "content": query}]
        }

        previous_content = ""
        try:
            # stream_mode="values" 逐值流式输出
            # 传入Token追踪回调 (#10)
            callbacks = [TokenTrackingCallbackHandler(source="knowledge")]
            for chunk in self.agent.stream(
                input_dict, stream_mode="values",
                context={"report": False},
                config={"callbacks": callbacks}
            ):
                latest_message = chunk["messages"][-1]
                if latest_message.content:
                    current_content = latest_message.content.strip()
                    # 只返回新增的部分，避免重复输出
                    new_content = current_content[len(previous_content):]
                    previous_content = current_content
                    if new_content:
                        yield new_content
        except Exception as e:
            logger.error(f"[KnowledgeAgent] 执行失败: {e}")
            yield f"抱歉，知识检索过程中出现错误，请稍后再试。"
