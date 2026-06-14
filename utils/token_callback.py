"""
LangChain Token追踪回调处理器 (#10)

在LLM调用完成后自动记录Token消耗到TokenTracker。
通过LangChain的回调机制，无需修改每个Agent的代码即可实现追踪。

使用方式：
    from utils.token_callback import TokenTrackingCallbackHandler

    # 在Agent stream/invoke时传入
    agent.stream(input_dict, callbacks=[TokenTrackingCallbackHandler(source="knowledge")])
"""

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, Optional
from utils.token_tracker import get_token_tracker
from utils.logger_handler import logger


class TokenTrackingCallbackHandler(BaseCallbackHandler):
    """
    Token追踪回调处理器

    继承LangChain的BaseCallbackHandler，在LLM调用结束时（on_llm_end）
    自动从响应中提取Token使用信息并记录到全局TokenTracker。

    Attributes:
        source: 调用来源标识（如 "supervisor"、"knowledge"、"weather"、"report"）
    """

    def __init__(self, source: str = "unknown"):
        """
        初始化回调处理器

        Args:
            source: 调用来源标识，用于区分不同Agent的Token消耗
        """
        self.source = source
        self._tracker = get_token_tracker()

    def on_llm_end(self, response: Any, **kwargs) -> None:
        """
        LLM调用结束时的回调

        从response中提取token_usage信息并记录。
        支持通义千问/ChatTongyi、OpenAI等主流模型的元数据格式。

        Args:
            response: LLM响应对象，包含usage_metadata或response_metadata
            **kwargs: 其他回调参数
        """
        try:
            input_tokens = 0
            output_tokens = 0

            # 方式1：LangChain标准 usage_metadata (推荐)
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                um = response.usage_metadata
                input_tokens = um.get('input_tokens', 0)
                output_tokens = um.get('output_tokens', 0)

            # 方式2：llm_output.token_usage (OpenAI/通义千问兼容格式)
            if input_tokens == 0 and hasattr(response, 'llm_output') and response.llm_output:
                metadata = response.llm_output.get('token_usage', {})
                if metadata:
                    input_tokens = metadata.get('prompt_tokens', 0)
                    output_tokens = metadata.get('completion_tokens', 0)

            # 方式3：response_metadata.usage (通义千问DashScope常用)
            if input_tokens == 0 and hasattr(response, 'response_metadata'):
                meta = response.response_metadata or {}
                if 'usage' in meta:
                    usage = meta['usage']
                    input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 0))
                    output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 0))
                elif 'token_usage' in meta:
                    tu = meta['token_usage']
                    input_tokens = tu.get('input_tokens', tu.get('prompt_tokens', 0))
                    output_tokens = tu.get('output_tokens', tu.get('completion_tokens', 0))

            # 方式4：直接从generations.message获取
            if input_tokens == 0:
                for msg in getattr(response, 'generations', []):
                    if hasattr(msg, 'message') and hasattr(msg.message, 'usage_metadata'):
                        um = msg.message.usage_metadata or {}
                        input_tokens = um.get('input_tokens', 0)
                        output_tokens = um.get('output_tokens', 0)
                        if input_tokens > 0:
                            break

            # 记录到追踪器
            if input_tokens > 0 or output_tokens > 0:
                self._tracker.record(
                    source=self.source,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            else:
                # 无法获取Token信息时输出调试信息（包含响应对象的可用属性）
                available_attrs = [a for a in dir(response) if not a.startswith('_') and 'token' in a.lower() or 'usage' in a.lower()]
                logger.debug(
                    f"[TokenCallback] {self.source}: 无法获取Token数据。"
                    f"响应类型: {type(response).__name__}, "
                    f"可用token相关属性: {available_attrs}"
                )

        except Exception as e:
            logger.warning(f"[TokenCallback] Token追踪回调异常: {e}")

    def on_llm_start(self, serialized: Dict, prompts: list, **kwargs) -> None:
        """LLM调用开始时的回调，用于记录seriaized信息辅助调试"""
        pass

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """LLM调用错误时的回调"""
        pass
