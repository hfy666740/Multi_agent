"""
BM25关键词检索器

基于 jieba 中文分词和 rank_bm25 的 BM25Okapi 算法，
提供关键词级别的文档检索能力，作为语义检索的补充。
"""
from typing import List, Tuple
from rank_bm25 import BM25Okapi
import jieba
from langchain_core.documents import Document
from utils.logger_handler import logger


class KeywordRetriever:
    """
    BM25关键词检索器

    使用 jieba 进行中文分词，基于 BM25 算法计算查询与文档的相关性分数。
    文档加载后需要调用 build_index() 构建索引，之后即可通过 retrieve() 检索。

    Attributes:
        _documents: 原始LangChain Document列表
        _corpus: 分词后的文档文本列表
        _bm25: BM25Okapi实例
        _is_built: 索引是否已构建
    """

    def __init__(self):
        self._documents: List[Document] = []
        self._corpus: List[List[str]] = []
        self._bm25: BM25Okapi = None
        self._is_built: bool = False

    def build_index(self, documents: List[Document]):
        """
        基于文档列表构建BM25索引

        对每个文档的page_content进行jieba分词，构建BM25Okapi索引。
        支持增量构建：如果已有索引，新文档会追加到现有索引中。

        Args:
            documents: LangChain Document列表
        """
        if not documents:
            logger.warning("[KeywordRetriever] 文档列表为空，跳过索引构建")
            return

        new_tokens = []
        for doc in documents:
            # 使用jieba精确模式分词
            tokens = list(jieba.cut(doc.page_content, cut_all=False))
            # 过滤空白字符
            tokens = [t.strip() for t in tokens if t.strip()]
            new_tokens.append(tokens)
            self._documents.append(doc)
            self._corpus.append(tokens)

        # 重建BM25索引（包含所有文档）
        self._bm25 = BM25Okapi(self._corpus)
        self._is_built = True
        logger.info(
            f"[KeywordRetriever] BM25索引构建完成，当前文档数: {len(self._documents)}"
        )

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """
        使用BM25算法检索与查询最相关的文档

        Args:
            query: 查询文本
            k: 返回的文档数量

        Returns:
            按相关性降序排列的Document列表
        """
        if not self._is_built:
            logger.warning("[KeywordRetriever] 索引未构建，返回空结果")
            return []

        # 对查询进行分词
        query_tokens = list(jieba.cut(query, cut_all=False))
        query_tokens = [t.strip() for t in query_tokens if t.strip()]

        if not query_tokens:
            return []

        # BM25检索，返回(document_index, score)元组
        scores = self._bm25.get_scores(query_tokens)

        # 按分数降序排列，取前k个
        # 使用argsort获取排序索引
        import numpy as np
        top_k_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_k_indices:
            if scores[idx] > 0:  # 只返回有相关性的文档
                results.append(self._documents[idx])

        logger.debug(
            f"[KeywordRetriever] 检索完成: query='{query[:50]}', "
            f"返回 {len(results)}/{k} 个文档"
        )
        return results

    @property
    def is_built(self) -> bool:
        """索引是否已构建"""
        return self._is_built

    @property
    def document_count(self) -> int:
        """当前索引中的文档数量"""
        return len(self._documents)