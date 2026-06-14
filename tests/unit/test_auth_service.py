# test_auth_service.py — 用户认证服务单元测试
# 技术栈: pytest (测试框架), unittest.mock (依赖模拟), bcrypt (密码哈希), PyJWT (Token)

import pytest
from unittest.mock import MagicMock, patch
from utils.auth_service import AuthService


class TestAuthService:
    """AuthService 认证服务单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("utils.auth_service.psycopg2") as mock_psycopg2:
            self.mock_conn = MagicMock()
            self.mock_cursor = MagicMock()
            self.mock_conn.cursor.return_value = self.mock_cursor
            mock_psycopg2.connect.return_value = self.mock_conn
            self.service = AuthService()
            yield

    def test_register_success(self):
        self.mock_cursor.fetchone.side_effect = [None, (1, "testuser", "test@example.com", "user")]
        result = self.service.register("testuser", "test@example.com", "SecurePass123!")
        assert result["success"] is True
        assert result["user"]["username"] == "testuser"

    def test_register_duplicate_username(self):
        self.mock_cursor.fetchone.return_value = (1,)
        result = self.service.register("existing", "test@example.com", "SecurePass123!")
        assert result["success"] is False
        assert "已存在" in result["message"]

    def test_login_success(self):
        with patch("utils.auth_service.bcrypt.checkpw") as mock_check:
            mock_check.return_value = True
            self.mock_cursor.fetchone.return_value = {
                "id": 1, "username": "testuser", "email": "test@example.com",
                "password_hash": "$2b$12$hash", "role": "user", "is_active": True
            }
            result = self.service.login("testuser", "correct_password")
            assert result["success"] is True
            assert "token" in result

    def test_login_wrong_password(self):
        with patch("utils.auth_service.bcrypt.checkpw") as mock_check:
            mock_check.return_value = False
            self.mock_cursor.fetchone.return_value = {
                "id": 1, "username": "testuser",
                "password_hash": "$2b$12$hash", "role": "user", "is_active": True
            }
            result = self.service.login("testuser", "wrong_password")
            assert result["success"] is False

    def test_login_inactive_user(self):
        self.mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser",
            "password_hash": "$2b$12$hash", "role": "user", "is_active": False
        }
        result = self.service.login("testuser", "any_password")
        assert result["success"] is False

    def test_verify_token_valid(self):
        with patch("utils.auth_service.jwt.decode") as mock_decode:
            mock_decode.return_value = {"user_id": 1, "username": "testuser", "role": "user"}
            result = self.service.verify_token("valid_token")
            assert result is not None
            assert result["user_id"] == 1

    def test_verify_token_expired(self):
        from jwt import ExpiredSignatureError
        with patch("utils.auth_service.jwt.decode") as mock_decode:
            mock_decode.side_effect = ExpiredSignatureError()
            result = self.service.verify_token("expired_token")
            assert result is None
