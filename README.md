[README.md](https://github.com/user-attachments/files/28938055/README.md)[Uploa# 智扫通 — 多Agent协作RAG智能客服系统

> 面向扫地机器人领域的智能客服问答平台，支持多 Agent 协作、混合检索 RAG、流式对话、Token 成本监控。

## 项目架构

```
用户 → Vue3前端 → FastAPI后端 → MultiAgentWorkflow
                                    │
                              ┌─────┴────────┐
                         Supervisor (意图路由)
                    ┌───┬────┬────┼────┐
                  知识  天气 报告  直接回复
                   ↓    ↓    ↓     ↓
                RAG混合  外部 数据   LLM
               检索引擎  API  聚合
```

### 多 Agent 协作流程

| Agent | 职责 | 说明 |
|-------|------|------|
| **Supervisor** | 意图识别与路由分发 | LLM 判断用户意图，路由到对应 Specialist Agent。闲聊问题直接回复，减少 Token 消耗 |
| **Knowledge Agent** | 产品知识问答 | 调用 RAG 混合检索引擎，回答扫地机器人产品知识 |
| **Weather Agent** | 天气查询 | 调用外部天气 API，回答天气相关问题 |
| **Report Agent** | 报告生成 | 聚合知识和天气信息，生成综合分析报告 |

### RAG 混合检索

| 检索方式 | 技术 | 说明 |
|---------|------|------|
| **语义检索** | ChromaDB 向量库 + text-embedding-v4 | 理解语义相似度，处理同义词和自然语言表达 |
| **关键词检索** | jieba 分词 + BM25 算法 | 精确匹配专有名词、产品型号（如："科沃斯T30"） |
| **RRF 融合** | Reciprocal Rank Fusion | 对双路检索结果加权重排序，取 Top-K |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 / FastAPI / LangChain |
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Axios |
| 数据库 | PostgreSQL（psycopg2）+ Alembic |
| 向量库 | ChromaDB（语义检索） |
| 大模型 | 通义千问 Qwen3-Max（阿里云 DashScope API） |
| Embedding | text-embedding-v4（阿里云） |
| 中文分词 | jieba + rank_bm25 |
| 可观测性 | LangSmith 链路追踪、自定义 Token 统计面板 |

## 快速开始

### 前置条件

- Python ≥ 3.10
- Node.js ≥ 18
- PostgreSQL ≥ 15（可用 Docker 启动）
- 阿里云 DashScope API Key（[免费申请](https://dashscope.aliyun.com)）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd ai-customer-service
```

### 2. 配置环境变量

复制环境变量模板并填入你的密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少要配置：

| 变量 | 说明 | 获取方式 |
|------|------|---------|
| `DASHSCOPE_API_KEY` | 通义千问 API Key | https://dashscope.aliyun.com |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | PostgreSQL 连接串 | 根据你的数据库配置填写 |
| `LANGCHAIN_TRACING_V2` | LangSmith 开关 | 可选，设为 `true` 启用追踪 |

### 3. 安装后端依赖

```bash
pip install -e .
```

安装开发工具（可选）：

```bash
pip install -e ".[dev]"
```

### 4. 启动 PostgreSQL 数据库

**方式一：使用 Docker（推荐）**

```bash
docker compose up -d postgres
```

**方式二：使用本地 PostgreSQL**

创建数据库：

```bash
createdb agent_chat
```

### 5. 初始化数据库

```bash
python scripts/init_postgres.py
```

### 6. 安装前端依赖

```bash
cd frontend
npm install
```

### 7. 运行项目

**启动后端 API 服务（终端一）：**

```bash
# 方式一：Makefile
make dev

# 方式二：直接运行
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档自动生成：http://localhost:8000/docs

**启动前端开发服务器（终端二）：**

```bash
cd frontend
npm run dev
```

前端访问地址：http://localhost:5173

### 8. 启动所有服务（Docker）

```bash
docker compose up -d
```

## 项目结构

```
ai-customer-service/
├── api/
│   └── main.py              # FastAPI 后端入口（路由、认证、聊天接口）
├── agent/
│   ├── workflow.py           # 多 Agent 编排器（总入口）
│   ├── supervisor.py         # Supervisor Agent（意图分类路由）
│   ├── react_agent.py        # 单 Agent 实现（独立可运行）
│   └── specialists/
│       ├── knowledge_agent.py  # 知识问答 Agent
│       ├── weather_agent.py    # 天气查询 Agent
│       └── report_agent.py     # 报告生成 Agent
├── rag/
│   ├── rag_service.py        # RAG 检索+生成服务
│   ├── vector_store.py       # ChromaDB 向量存储与检索
│   ├── hybrid_retriever.py   # 混合检索器（语义+关键词 RRF 融合）
│   └── keyword_retriever.py  # BM25 关键词检索器
├── model/
│   └── factory.py            # LLM / Embedding 模型工厂
├── models/
│   └── db_models.py          # 数据库 ORM 模型（SQLAlchemy）
├── utils/
│   ├── token_callback.py     # LangChain 回调自动采集 Token
│   ├── token_tracker.py      # Token 统计（内存 + 数据库双写）
│   ├── token_stats_service.py # Token 持久化服务
│   ├── langsmith_tracker.py  # LangSmith 追踪配置
│   ├── prompt_loader.py      # 提示词统一加载
│   ├── db_pool.py            # 数据库连接池
│   ├── logger_handler.py     # 日志配置
│   └── auth.py               # JWT 认证工具
├── config/
│   └── *.yml                 # 配置文件（数据库、模型、RAG、Agent）
├── scripts/
│   └── init_postgres.py      # 数据库初始化脚本
├── frontend/                 # Vue3 前端
│   └── src/
│       ├── views/
│       │   ├── Chat.vue      # 聊天界面（含 Token 统计面板）
│       │   ├── Knowledge.vue # 知识库管理
│       │   └── Login.vue     # 登录注册
│       ├── stores/           # Pinia 状态管理
│       ├── router/           # Vue Router 路由
│       └── api/              # Axios API 封装
├── .env                      # 环境变量（敏感信息！勿提交）
├── .env.example              # 环境变量模板
├── pyproject.toml            # Python 项目配置与依赖
├── docker-compose.yml        # Docker 编排
└── alembic/                  # 数据库迁移
```

## 主要功能

### 聊天问答

- 支持多轮对话、流式输出（SSE）
- Supervisor 智能路由，自动识别用户意图
- RAG 混合检索，精准回答产品知识问题

### Token 成本监控

- 自动采集每次 LLM 调用的 Token 消耗，按 Agent 来源分类统计
- 内存 + PostgreSQL 双写策略，数据库异常不影响业务
- RESTful API 暴露统计数据（`GET /api/stats/tokens`）
- 前端可折叠面板实时展示 Token 用量

### 知识库管理

- 上传文档（PDF/TXT），自动向量化存储
- 支持 BM25 关键词索引增量构建
- 删除、重载知识库

## 常用命令

```bash
make dev              # 启动开发服务器
make test             # 运行测试
make lint             # 代码检查（ruff）
make format           # 代码格式化
make migrate          # 数据库迁移
make db-shell         # 进入数据库
```

## License

MITding README.md…]()

