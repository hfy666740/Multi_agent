"""
会话存储服务类 - 使用 PostgreSQL 存储历史会话
核心服务类，提供会话的CRUD操作：
 - 创建会话
 - 保存消息
 - 获取会话消息
 - 获取所有会话
 - 删除会话
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
from utils.config_handler import database_conf
from utils.logger_handler import logger
import uuid
from datetime import datetime


class ChatSessionService:
    def __init__(self):
        self.db_config = database_conf
        self._ensure_connection()
    
    def _get_connection(self):
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database']
        )
    
    def _ensure_connection(self):
        try:
            conn = self._get_connection()
            conn.close()
            logger.info("[数据库连接] PostgreSQL 连接成功")
        except Exception as e:
            logger.error(f"[数据库连接] PostgreSQL 连接失败: {e}")
    
    def create_session(self, user_id: Optional[int] = None) -> str:
        session_id = str(uuid.uuid4())
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id, user_id) VALUES (%s, %s) RETURNING session_id",
                    (session_id, user_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id) VALUES (%s) RETURNING session_id",
                    (session_id,)
                )
            conn.commit()
            logger.info(f"[会话创建] 新会话创建成功: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"[会话创建] 创建会话失败: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def save_message(self, session_id: str, role: str, content: str) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content)
            )
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()
            logger.info(f"[消息保存] 会话 {session_id} 保存消息成功, 角色: {role}")
            return True
        except Exception as e:
            logger.error(f"[消息保存] 保存消息失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT role, content, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
                (session_id,)
            )
            messages = cursor.fetchall()
            result = []
            for msg in messages:
                msg_dict = dict(msg)
                if isinstance(msg_dict.get('created_at'), datetime):
                    msg_dict['created_at'] = msg_dict['created_at'].isoformat()
                result.append(msg_dict)
            return result
        except Exception as e:
            logger.error(f"[消息获取] 获取会话消息失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_latest_session(self, user_id: Optional[int] = None) -> Optional[Dict]:
        """获取用户最近一次会话"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            if user_id:
                cursor.execute(
                    "SELECT session_id, created_at, updated_at FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "SELECT session_id, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 1"
                )
            session = cursor.fetchone()
            if not session:
                return None
            result = dict(session)
            if isinstance(result.get('created_at'), datetime):
                result['created_at'] = result['created_at'].isoformat()
            if isinstance(result.get('updated_at'), datetime):
                result['updated_at'] = result['updated_at'].isoformat()
            return result
        except Exception as e:
            logger.error(f"[最新会话] 获取最新会话失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_all_sessions(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if user_id:
                cursor.execute(
                    """
                    SELECT s.session_id, s.created_at, s.updated_at,
                           COUNT(m.id) as message_count,
                           FIRST_VALUE(m.content) OVER (PARTITION BY s.session_id ORDER BY m.created_at) as first_message
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    WHERE s.user_id = %s
                    GROUP BY s.session_id, s.created_at, s.updated_at, m.content, m.created_at
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT s.session_id, s.created_at, s.updated_at,
                           COUNT(m.id) as message_count,
                           FIRST_VALUE(m.content) OVER (PARTITION BY s.session_id ORDER BY m.created_at) as first_message
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    GROUP BY s.session_id, s.created_at, s.updated_at, m.content, m.created_at
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
            sessions = cursor.fetchall()
            result = []
            seen_sessions = set()
            for s in sessions:
                session_dict = dict(s)
                if session_dict['session_id'] not in seen_sessions:
                    seen_sessions.add(session_dict['session_id'])
                    # 使用第一条消息作为标题，最多显示30个字符
                    first_msg = session_dict.pop('first_message', None)
                    if first_msg:
                        session_dict['title'] = first_msg[:30] + '...' if len(first_msg) > 30 else first_msg
                    else:
                        session_dict['title'] = '新对话'
                    result.append(session_dict)
            return result
        except Exception as e:
            logger.error(f"[会话列表] 获取会话列表失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def delete_session(self, session_id: str) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            conn.commit()
            logger.info(f"[会话删除] 会话 {session_id} 删除成功")
            return True
        except Exception as e:
            logger.error(f"[会话删除] 删除会话失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def session_exists(self, session_id: str) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"[会话检查] 检查会话是否存在失败: {e}")
            return False
        finally:
            if conn:
                conn.close()


if __name__ == '__main__':
    service = ChatSessionService()
    
    session_id = service.create_session()
    print(f"创建会话: {session_id}")
    
    service.save_message(session_id, "user", "你好，我想咨询扫地机器人")
    service.save_message(session_id, "assistant", "您好！请问有什么可以帮助您的？")
    
    messages = service.get_session_messages(session_id)
    print(f"会话消息: {messages}")
    
    sessions = service.get_all_sessions()
    print(f"所有会话: {sessions}")