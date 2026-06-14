-- 创建数据库（如果不存在）
-- 注意：需要先以 postgres 用户登录执行 CREATE DATABASE

-- 创建会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);

-- 添加注释
COMMENT ON TABLE chat_sessions IS '聊天会话表';
COMMENT ON TABLE chat_messages IS '聊天消息表';
COMMENT ON COLUMN chat_sessions.session_id IS '会话唯一标识';
COMMENT ON COLUMN chat_messages.role IS '消息角色: user/assistant';
COMMENT ON COLUMN chat_messages.content IS '消息内容';

-- 创建Token使用记录表
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_token_usage_source ON token_usage(source);
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);

-- 添加注释
COMMENT ON TABLE token_usage IS 'Token使用记录表';
COMMENT ON COLUMN token_usage.source IS '调用来源: supervisor/knowledge/weather/report/direct';
COMMENT ON COLUMN token_usage.input_tokens IS '输入（Prompt）Token数';
COMMENT ON COLUMN token_usage.output_tokens IS '输出（Completion）Token数';
COMMENT ON COLUMN token_usage.total_tokens IS '总Token数';
COMMENT ON COLUMN token_usage.session_id IS '关联的会话ID';