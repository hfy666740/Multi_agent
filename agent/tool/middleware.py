"""
middleware.py — Agent 中间件集合
技术栈: LangChain (Agent 中间件), Token 追踪
用途: Agent 执行过程中的监控、日志记录、prompt 切换等中间件
"""
from typing import Callable, Any
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
from utils.prompt_loader import load_system_prompt, load_report_prompt


@wrap_tool_call
def monitor_tool(
        request: ToolCallRequest,   #工具调用请求对象，包含工具调用的相关信息，如工具名称、参数等
        handler: Callable[[ToolCallRequest], ToolMessage | Command]   #工具调用处理函数，接受一个ToolCallRequest对象作为参数，并返回一个ToolMessage对象或Command对象
) -> ToolMessage | Command:
    logger.info(f"[tool monitor]执行工具: {request.tool_call['name']}")
    logger.info(f"[tool monitor]参数: {request.tool_call['args']}")
    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")

        if request.tool_call['name'] == 'fill_context_for_report':
            logger.info(f"[tool monitor]fill_context_for_report工具被调用，注入上下文 report=True")
            request.runtime.context["report"] = True
        return result
    except Exception as e:
        logger.info(f"工具{request.tool_call['name']}调用失败: {e}")
        raise


@before_model
def log_before_model(state:AgentState, runtime: Runtime) -> dict[str, Any] | None:
    logger.info(f"[log_before_model]: 即将调用模型，带有{len(state['messages'])}条消息，消息如下：")
    # for message in state['messages']:
    #     logger.info(f"[log_before_model][{type(message).__name__}]: {message.content.strip()}")
    logger.info(f"[log_before_model]: ----------省略已输出内容----------")
    logger.info(f"[log_before_model][{type(state['messages'][-1]).__name__}]: {state['messages'][-1].content.strip()}")


    return None

@dynamic_prompt     #每一次在生成模型调用之前都会调用这个函数，根据runtime中的上下文信息来决定使用哪个提示词
def report_prompt_switch(request: ModelRequest) -> str: #动态切换提示词
    is_report = request.runtime.context.get("report", False)
    if is_report:                               #是报告生成场景，返回报告生成的提示词
        return load_report_prompt()

    return load_system_prompt()














