"""
LangSmith 追踪初始化

LangSmith 是 LangChain 官方的可观测性平台，通过环境变量自动启用追踪后，
所有 LangChain runnable 的 LLM/Chain/Agent 调用都会自动上报到 LangSmith 平台。

启用方式（无需修改任何业务代码）：
    在 .env 或环境变量中设置：
        LANGCHAIN_TRACING_V2=true
        LANGCHAIN_API_KEY=<你的 LangSmith API Key>
        LANGCHAIN_PROJECT=<项目名称>

本模块提供：
    1. is_langsmith_enabled(): 检查LangSmith是否启用
    2. get_langsmith_project(): 获取当前项目名
    3. set_langsmith_env(): 代码中动态设置环境变量

参考文档：
    https://docs.smith.langchain.com/
"""
import os
from typing import Optional
from utils.logger_handler import logger


# LangSmith默认项目名
DEFAULT_LANGSMITH_PROJECT = "ai-customer-service"

# 标记是否在本次进程启动时启用了LangSmith（用于日志去重）
_logged_status = False


def is_langsmith_enabled() -> bool:
    """
    检查LangSmith追踪是否启用

    Returns:
        bool: True表示已启用
    """
    return (
        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
        and bool(os.environ.get("LANGCHAIN_API_KEY", ""))
    )


def get_langsmith_project() -> str:
    """
    获取当前LangSmith项目名

    Returns:
        str: 项目名称，默认值 DEFAULT_LANGSMITH_PROJECT
    """
    return os.environ.get("LANGCHAIN_PROJECT", DEFAULT_LANGSMITH_PROJECT)


def set_langsmith_env(api_key: str, project: str = DEFAULT_LANGSMITH_PROJECT,
                     endpoint: Optional[str] = None) -> None:
    """
    代码中动态启用LangSmith追踪

    等价于在环境中设置：
        LANGCHAIN_TRACING_V2=true
        LANGCHAIN_API_KEY=<api_key>
        LANGCHAIN_PROJECT=<project>

    Args:
        api_key: LangSmith API Key
        project: 项目名称
        endpoint: LangSmith服务端点（自部署场景）
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    logger.info(f"[LangSmith] 已动态启用追踪，项目: {project}")


def log_langsmith_status() -> None:
    """
    启动时打印LangSmith追踪状态（仅打印一次）
    """
    global _logged_status
    if _logged_status:
        return
    _logged_status = True

    if is_langsmith_enabled():
        logger.info(
            f"[LangSmith] 追踪已启用 | 项目: {get_langsmith_project()} | "
            f"可在 https://smith.langchain.com 查看追踪数据"
        )
    else:
        logger.info(
            "[LangSmith] 追踪未启用 | 如需启用请设置环境变量 "
            "LANGCHAIN_TRACING_V2=true 和 LANGCHAIN_API_KEY=<key>"
        )
