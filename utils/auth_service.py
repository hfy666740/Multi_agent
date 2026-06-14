"""
用户认证服务类
提供用户注册、登录、JWT令牌管理等功能

安全特性 (#5):
- JWT密钥从环境变量读取，不再硬编码
- 生产环境必须设置 JWT_SECRET_KEY 环境变量
- 开发环境使用默认值（仅限本地测试）
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict
from utils.config_handler import database_conf
from utils.logger_handler import logger
import bcrypt
import jwt
from datetime import datetime, timedelta
import uuid

# 从环境变量读取JWT密钥，开发环境有默认值，生产环境必须配置 (#5)
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

class AuthService:
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
            logger.info("[认证服务] PostgreSQL 连接成功")
        except Exception as e:
            logger.error(f"[认证服务] PostgreSQL 连接失败: {e}")
    
    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _generate_token(self, user_id: int, username: str, role: str) -> str:
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow(),
            'jti': str(uuid.uuid4())
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def register(self, username: str, email: str, password: str) -> Dict:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {'success': False, 'message': '用户名已存在'}
            
            cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {'success': False, 'message': '邮箱已被注册'}
            
            password_hash = self._hash_password(password)
            
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id, username, email, role",
                (username, email, password_hash)
            )
            user = cursor.fetchone()
            conn.commit()
            
            logger.info(f"[用户注册] 用户注册成功: {username}")
            return {
                'success': True,
                'message': '注册成功',
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3]
                }
            }
        except Exception as e:
            logger.error(f"[用户注册] 注册失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def login(self, username: str, password: str) -> Dict:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT id, username, email, password_hash, role, is_active FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'message': '用户名或密码错误'}
            
            if not user['is_active']:
                return {'success': False, 'message': '用户已被禁用'}
            
            if not self._verify_password(password, user['password_hash']):
                return {'success': False, 'message': '用户名或密码错误'}
            
            token = self._generate_token(user['id'], user['username'], user['role'])
            
            logger.info(f"[用户登录] 用户登录成功: {username}")
            return {
                'success': True,
                'message': '登录成功',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            }
        except Exception as e:
            logger.error(f"[用户登录] 登录失败: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def verify_token(self, token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
        except jwt.ExpiredSignatureError:
            logger.warning("[Token验证] Token已过期")
            return None
        except jwt.InvalidTokenError:
            logger.warning("[Token验证] Token无效")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT id, username, email, role, is_active, created_at FROM users WHERE id = %s",
                (user_id,)
            )
            user = cursor.fetchone()
            
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"[获取用户] 获取用户失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def update_user(self, user_id: int, data: Dict) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_fields = []
            params = []
            
            if 'username' in data:
                update_fields.append("username = %s")
                params.append(data['username'])
            if 'email' in data:
                update_fields.append("email = %s")
                params.append(data['email'])
            if 'password' in data:
                update_fields.append("password_hash = %s")
                params.append(self._hash_password(data['password']))
            if 'role' in data:
                update_fields.append("role = %s")
                params.append(data['role'])
            if 'is_active' in data:
                update_fields.append("is_active = %s")
                params.append(data['is_active'])
            
            if not update_fields:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            
            cursor.execute(query, tuple(params))
            conn.commit()
            
            logger.info(f"[更新用户] 用户更新成功: {user_id}")
            return True
        except Exception as e:
            logger.error(f"[更新用户] 更新用户失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            
            logger.info(f"[删除用户] 用户删除成功: {user_id}")
            return True
        except Exception as e:
            logger.error(f"[删除用户] 删除用户失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

if __name__ == '__main__':
    auth = AuthService()
    
    # 测试注册
    # result = auth.register("testuser", "test@example.com", "password123")
    # print("注册结果:", result)
    
    # 测试登录
    # result = auth.login("testuser", "password123")
    # print("登录结果:", result)
    
    # 测试验证token
    # if result['success']:
    #     token = result['token']
    #     user_info = auth.verify_token(token)
    #     print("验证token:", user_info)