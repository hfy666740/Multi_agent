"""
混合检索器

使用RRF（Reciprocal Rank Fusion）算法融合语义检索和关键词检索的结果，
提升检索的准确率和召回率。
"""
from typing import List
from langchain_core.documents import Document
from utils.config_handler import rag_conf
from utils.logger_handler import logger


class HybridRetriever:
    """
    混合检索器

    同时执行语义检索（向量相似度）和关键词检索（BM25），
    通过RRF算法融合两个结果集，返回最终排序的Top-K文档。

    融合策略：
    1. 分别从语义检索器和关键词检索器获取候选文档
    2. 对每个候选文档计算RRF分数
    3. 按RRF分数降序排列，返回Top-K结果

    Attributes:
        semantic_retriever: 语义检索器（ChromaDB as_retriever）
        keyword_retriever: 关键词检索器（KeywordRetriever实例）
        rrf_k: RRF算法平滑参数，默认60
        semantic_k: 语义检索返回数量
        keyword_k: 关键词检索返回数量
        final_k: 最终返回的文档数量
    """

    def __init__(self, semantic_retriever, keyword_retriever):
        """
        初始化混合检索器

        Args:
            semantic_retriever: ChromaDB的语义检索器
            keyword_retriever: KeywordRetriever实例
        """
        self.semantic_retriever = semantic_retriever
        self.keyword_retriever = keyword_retriever

        # 从配置读取参数，提供默认值
        self.rrf_k = rag_conf.get('rrf_k', 60)
        self.semantic_k = rag_conf.get('semantic_k', 3)
        self.keyword_k = rag_conf.get('keyword_k', 3)
        self.final_k = rag_conf.get('k', 3)

        logger.info(
            f"[HybridRetriever] 初始化完成: rrf_k={self.rrf_k}, "
            f"semantic_k={self.semantic_k}, keyword_k={self.keyword_k}, "
            f"final_k={self.final_k}"
        )

    def invoke(self, query: str) -> List[Document]:
        """
        执行混合检索

        Args:
            query: 查询文本

        Returns:
            按RRF分数降序排列的Document列表
        """
        # 1. 语义检索
        try:
            semantic_docs = self.semantic_retriever.invoke(query)
            if not semantic_docs:
                semantic_docs = []
        except Exception as e:
            logger.warning(f"[HybridRetriever] 语义检索失败: {e}")
            semantic_docs = []

        # 2. 关键词检索
        try:
            keyword_docs = self.keyword_retriever.retrieve(query, k=self.keyword_k)
            if not keyword_docs:
                keyword_docs = []
        except Exception as e:
            logger.warning(f"[HybridRetriever] 关键词检索失败: {e}")
            keyword_docs = []

        # 如果其中一个检索器返回空结果，直接返回另一个的结果
        if not semantic_docs and not keyword_docs:
            return []
        if not semantic_docs:
            return keyword_docs[:self.final_k]
        if not keyword_docs:
            return semantic_docs[:self.final_k]

        # 3. RRF融合
        # 使用page_content作为文档唯一标识（简单去重）
        rrf_scores = {}

        # 计算语义检索的RRF分数
        for rank, doc in enumerate(semantic_docs, start=1):
            doc_key = doc.page_content[:100]  # 使用前100字符作为标识
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0) + 1.0 / (self.rrf_k + rank)
            # 保存文档引用
            if not hasattr(self, '_doc_map'):
                self._doc_map = {}
            self._doc_map[doc_key] = doc

        # 计算关键词检索的RRF分数
        for rank, doc in enumerate(keyword_docs, start=1):
            doc_key = doc.page_content[:100]
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0) + 1.0 / (self.rrf_k + rank)
            if not hasattr(self, '_doc_map'):
                self._doc_map = {}
            self._doc_map[doc_key] = doc

        # 按RRF分数降序排列
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # 取前final_k个
        result = []
        for doc_key, score in sorted_docs[:self.final_k]:
            doc = self._doc_map.get(doc_key)
            if doc:
                # 将RRF分数添加到metadata中
                doc.metadata['rrf_score'] = round(score, 6)
                result.append(doc)

        logger.debug(
            f"[HybridRetriever] 混合检索完成: 语义={len(semantic_docs)}, "
            f"关键词={len(keyword_docs)}, 融合后={len(result)}"
        )
        return result