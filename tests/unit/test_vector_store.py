# test_vector_store.py — 向量库服务单元测试
# 技术栈: pytest (测试框架), unittest.mock (ChromaDB 模拟), LangChain Chroma (向量存储)

import pytest
from unittest.mock import MagicMock, patch, mock_open


class TestVectorStoreService:
    """向量库服务单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("rag.vector_store.Chroma") as mock_chroma, \
             patch("rag.vector_store.embed_model") as mock_embed, \
             patch("rag.vector_store.chroma_conf", {
                 "collection_name": "test",
                 "persist_directory": "chroma_db",
                 "data_path": "data",
                 "md5_hex_store": "md5.text",
                 "chunk_size": 200, "chunk_overlap": 20,
                 "separators": ["\n\n", "\n", "。"],
                 "k": 3,
                 "allow_knowledge_file_type": [".txt", ".pdf", ".csv"]
             }):
            mock_chroma_instance = MagicMock()
            mock_chroma.return_value = mock_chroma_instance
            mock_embed.embed_query.return_value = [0.1] * 768
            from rag.vector_store import VectorStoreService
            self.service = VectorStoreService()
            yield

    def test_get_retriever(self):
        retriever = self.service.get_retriever()
        assert retriever is not None

    def test_get_hybrid_retriever(self):
        hybrid = self.service.get_hybrid_retriever()
        assert hybrid is not None

    def test_load_documents_skip_loaded(self):
        with patch("rag.vector_store.listdir_with_allowed_type") as mock_listdir, \
             patch("rag.vector_store.get_file_md5") as mock_md5, \
             patch("builtins.open", mock_open(read_data="existing_md5\n")):
            mock_listdir.return_value = ["data/test.txt"]
            mock_md5.return_value = "existing_md5"
            self.service.load_documents()

    def test_load_documents_new_file(self):
        with patch("rag.vector_store.listdir_with_allowed_type") as mock_listdir, \
             patch("rag.vector_store.get_file_md5") as mock_md5, \
             patch("rag.vector_store.txt_loader") as mock_txt_loader, \
             patch("builtins.open", mock_open(read_data="")):
            mock_listdir.return_value = ["data/new_test.txt"]
            mock_md5.return_value = "new_md5_hex"
            from langchain_core.documents import Document
            mock_txt_loader.return_value = [Document(page_content="测试文档内容")]
            self.service.load_documents()
            assert self.service.vector_store.add_documents.called
