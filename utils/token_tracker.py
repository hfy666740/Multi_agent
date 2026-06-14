"""
Token成本追踪器 (#10)

功能：
1. 追踪每次LLM调用的Token消耗（输入Token、输出Token、总Token）
2. 记录调用来源（Supervisor / KnowledgeAgent / WeatherAgent / ReportAgent）
3. 提供统计查询接口，便于后续接入计费系统

使用方式：
    from utils.token_tracker import TokenTracker, get_token_tracker

    # 在Agent中使用
    tracker = get_token_tracker()
    tracker.record("knowledge", input_tokens=150, output_tokens=300)

    # 查询统计
    stats = tracker.get_stats()
"""

import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from utils.logger_handler import logger
from utils.token_stats_service import get_token_stats_service


@dataclass
class TokenUsage:
    """单次LLM调用的Token使用记录"""
    source: str           # 调用来源：supervisor/knowledge/weather/report/direct
    input_tokens: int     # 输入Token数
    output_tokens: int    # 输出Token数
    total_tokens: int     # 总Token数
    timestamp: float      # 调用时间戳


class TokenTracker:
    """
    Token成本追踪器

    线程安全的设计，支持多线程并发记录。
    所有记录保存在内存中，按时间窗口统计。

    Attributes:
        _records: Token使用记录列表（线程锁保护）
        _lock: 线程锁，保证并发安全
    """

    def __init__(self):
        self._records: List[TokenUsage] = []
        self._lock = threading.Lock()
        self._stats_service = None  # 延迟初始化，避免循环导入
        logger.info("[TokenTracker] Token追踪器初始化完成")

    def record(self, source: str, input_tokens: int = 0, output_tokens: int = 0,
               total_tokens: Optional[int] = None):
        """
        记录一次LLM调用的Token消耗

        Args:
            source: 调用来源标识，如 "supervisor"、"knowledge"、"weather"、"report"
            input_tokens: 输入（Prompt）Token数
            output_tokens: 输出（Completion）Token数
            total_tokens: 总Token数，如果不传则自动计算为 input + output
        """
        if total_tokens is None:
            total_tokens = input_tokens + output_tokens

        usage = TokenUsage(
            source=source,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            timestamp=time.time()
        )

        with self._lock:
            self._records.append(usage)

        # 同步写入数据库（降级：失败不影响内存记录）
        try:
            if self._stats_service is None:
                from utils.token_stats_service import get_token_stats_service
                self._stats_service = get_token_stats_service()
            self._stats_service.record_usage(
                source=source,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens
            )
        except Exception as e:
            logger.debug(f"[TokenTracker] 数据库写入失败（降级为仅内存记录）: {e}")

        logger.debug(
            f"[TokenTracker] {source}: "
            f"input={input_tokens}, output={output_tokens}, total={total_tokens}"
        )

    def get_stats(self) -> Dict:
        """
        获取当前会话的Token使用统计

        Returns:
            包含各来源和总计的统计信息字典
        """
        with self._lock:
            records = list(self._records)

        if not records:
            return {"total_calls": 0, "total_input": 0, "total_output": 0, "by_source": {}}

        stats = {
            "total_calls": len(records),
            "total_input": sum(r.input_tokens for r in records),
            "total_output": sum(r.output_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "by_source": {}
        }

        # 按来源分组统计
        for r in records:
            if r.source not in stats["by_source"]:
                stats["by_source"][r.source] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }
            s = stats["by_source"][r.source]
            s["calls"] += 1
            s["input_tokens"] += r.input_tokens
            s["output_tokens"] += r.output_tokens
            s["total_tokens"] += r.total_tokens

        return stats

    def reset(self):
        """清空所有记录"""
        with self._lock:
            self._records.clear()


# 全局单例实例
_token_tracker_instance: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """
    获取全局Token追踪器单例

    Returns:
        TokenTracker单例实例
    """
    global _token_tracker_instance
    if _token_tracker_instance is None:
        _token_tracker_instance = TokenTracker()
    return _token_tracker_instance
