# test_rag_service.py — RAG 检索服务单元测试
# 技术栈: pytest (测试框架), unittest.mock (依赖模拟), LangChain (RAG 链路)

import pytest
from unittest.mock import MagicMock, patch


class TestRagSummarizeService:
    """RAG 摘要服务单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("rag.rag_service.VectorStoreService") as mock_vs, \
             patch("rag.rag_service.chat_model") as mock_llm, \
             patch("rag.rag_service.rag_conf", {"retrieval_mode": "semantic"}):
            mock_retriever = MagicMock()
            mock_retriever.invoke.return_value = []
            mock_vs_instance = MagicMock()
            mock_vs_instance.get_retriever.return_value = mock_retriever
            mock_vs.return_value = mock_vs_instance
            mock_llm.invoke.return_value.content = "测试回复内容"
            from rag.rag_service import RagSummarizeService
            self.service = RagSummarizeService()
            yield

    def test_retrieve_docs_empty(self):
        docs = self.service.retrieve_docs("")
        assert docs == []

    def test_retrieve_docs_with_query(self):
        from langchain_core.documents import Document
        self.service.retriever.invoke.return_value = [Document(page_content="测试文档内容")]
        docs = self.service.retrieve_docs("扫地机器人")
        assert len(docs) == 1

    def test_rag_summarize_success(self):
        from langchain_core.documents import Document
        self.service.retriever.invoke.return_value = [
            Document(page_content="尘盒位于机器人底部，按下卡扣即可打开")
        ]
        result = self.service.rag_summarize("如何清理尘盒？")
        assert result is not None
        assert len(result) > 10
