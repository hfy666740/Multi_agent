# conftest.py — Pytest 共享 fixtures 和全局配置
# 技术栈: pytest (测试框架), pytest-asyncio (异步测试), unittest.mock (模拟依赖)

import sys
import os
from pathlib import Path

# 将项目根目录加入 sys.path，确保测试能正确导入项目模块
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator, Any, Dict


# ============================================================
# 全局 Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def mock_logger():
    """自动 mock logger，避免测试时产生真实日志文件"""
    with patch("utils.logger_handler.logger") as mock_log:
        yield mock_log


@pytest.fixture
def mock_chat_model():
    """模拟 LLM ChatModel，返回预设响应"""
    mock = MagicMock()
    mock.invoke.return_value.content = "测试回复内容"
    return mock


@pytest.fixture
def mock_embed_model():
    """模拟 Embedding 模型"""
    mock = MagicMock()
    mock.embed_query.return_value = [0.1, 0.2, 0.3]
    return mock


@pytest.fixture
def mock_vector_store():
    """模拟 Chroma VectorStore"""
    mock = MagicMock()
    mock.similarity_search.return_value = []
    mock.as_retriever.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_db_connection():
    """模拟 PostgreSQL 数据库连接"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    return mock_conn


@pytest.fixture
def sample_query() -> str:
    """标准测试用用户查询"""
    return "扫地机器人怎么清理尘盒？"


@pytest.fixture
def sample_session_id() -> str:
    """标准测试用会话 ID"""
    return "test-session-uuid-12345"


@pytest.fixture
def sample_user() -> Dict[str, Any]:
    """标准测试用用户信息"""
    return {"user_id": 1, "username": "testuser", "role": "admin"}


@pytest.fixture
def mock_token_tracker():
    """模拟 Token 追踪器"""
    with patch("utils.token_tracker.get_token_tracker") as mock:
        tracker = MagicMock()
        tracker.get_stats.return_value = {
            "supervisor": {"calls": 1, "total_tokens": 100},
            "total": {"calls": 2, "total_tokens": 200},
        }
        mock.return_value = tracker
        yield mock
