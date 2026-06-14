"""
Token统计服务类
提供Token使用记录的持久化存储和查询功能
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
from utils.config_handler import database_conf
from utils.logger_handler import logger
from datetime import datetime


class TokenStatsService:
    """Token统计服务，负责Token使用记录的数据库CRUD操作"""
    
    def __init__(self):
        self.db_config = database_conf
        self._ensure_connection()
    
    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database']
        )
    
    def _ensure_connection(self):
        """验证数据库连接"""
        try:
            conn = self._get_connection()
            conn.close()
            logger.info("[TokenStatsService] PostgreSQL 连接成功")
        except Exception as e:
            logger.error(f"[TokenStatsService] PostgreSQL 连接失败: {e}")
    
    def record_usage(self, source: str, input_tokens: int, output_tokens: int,
                     total_tokens: Optional[int] = None, session_id: Optional[str] = None) -> bool:
        """
        记录一次Token使用
        
        Args:
            source: 调用来源 (supervisor/knowledge/weather/report/direct)
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            total_tokens: 总Token数，不传则自动计算
            session_id: 关联的会话ID
        
        Returns:
            bool: 是否记录成功
        """
        if total_tokens is None:
            total_tokens = input_tokens + output_tokens
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO token_usage (source, input_tokens, output_tokens, total_tokens, session_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (source, input_tokens, output_tokens, total_tokens, session_id)
            )
            conn.commit()
            logger.debug(
                f"[TokenStatsService] 记录Token: source={source}, "
                f"input={input_tokens}, output={output_tokens}, total={total_tokens}"
            )
            return True
        except Exception as e:
            logger.error(f"[TokenStatsService] 记录Token失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_stats(self, session_id: Optional[str] = None) -> Dict:
        """
        获取Token使用统计
        
        Args:
            session_id: 可选，按会话筛选
        
        Returns:
            统计信息字典
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if session_id:
                cursor.execute(
                    """SELECT source, COUNT(*) as calls, 
                              SUM(input_tokens) as input_tokens,
                              SUM(output_tokens) as output_tokens,
                              SUM(total_tokens) as total_tokens
                       FROM token_usage
                       WHERE session_id = %s
                       GROUP BY source""",
                    (session_id,)
                )
            else:
                cursor.execute(
                    """SELECT source, COUNT(*) as calls,
                              SUM(input_tokens) as input_tokens,
                              SUM(output_tokens) as output_tokens,
                              SUM(total_tokens) as total_tokens
                       FROM token_usage
                       GROUP BY source"""
                )
            
            rows = cursor.fetchall()
            
            stats = {
                "total_calls": 0,
                "total_input": 0,
                "total_output": 0,
                "total_tokens": 0,
                "by_source": {}
            }
            
            for row in rows:
                source = row['source']
                stats["total_calls"] += row['calls']
                stats["total_input"] += row['input_tokens']
                stats["total_output"] += row['output_tokens']
                stats["total_tokens"] += row['total_tokens']
                stats["by_source"][source] = {
                    "calls": row['calls'],
                    "input_tokens": row['input_tokens'],
                    "output_tokens": row['output_tokens'],
                    "total_tokens": row['total_tokens']
                }
            
            return stats
        except Exception as e:
            logger.error(f"[TokenStatsService] 查询统计失败: {e}")
            return {"total_calls": 0, "total_input": 0, "total_output": 0, "by_source": {}}
        finally:
            if conn:
                conn.close()
    
    def get_history(self, limit: int = 50, session_id: Optional[str] = None) -> List[Dict]:
        """
        获取Token使用历史记录
        
        Args:
            limit: 返回记录数上限
            session_id: 可选，按会话筛选
        
        Returns:
            历史记录列表
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if session_id:
                cursor.execute(
                    """SELECT id, source, input_tokens, output_tokens, total_tokens, 
                              session_id, created_at
                       FROM token_usage
                       WHERE session_id = %s
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (session_id, limit)
                )
            else:
                cursor.execute(
                    """SELECT id, source, input_tokens, output_tokens, total_tokens,
                              session_id, created_at
                       FROM token_usage
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,)
                )
            
            rows = cursor.fetchall()
            result = []
            for row in rows:
                record = dict(row)
                if isinstance(record.get('created_at'), datetime):
                    record['created_at'] = record['created_at'].isoformat()
                result.append(record)
            
            return result
        except Exception as e:
            logger.error(f"[TokenStatsService] 查询历史失败: {e}")
            return []
        finally:
            if conn:
                conn.close()


# 全局单例
_token_stats_service_instance: Optional[TokenStatsService] = None


def get_token_stats_service() -> TokenStatsService:
    """获取全局TokenStatsService单例"""
    global _token_stats_service_instance
    if _token_stats_service_instance is None:
        _token_stats_service_instance = TokenStatsService()
    return _token_stats_service_instance