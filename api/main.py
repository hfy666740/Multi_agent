"""
FastAPI 主应用入口
提供 REST API 服务，包含认证、聊天、会话管理、知识库管理等接口

企业级特性：
- 全局异常处理中间件（统一错误响应格式）
- API速率限制（防恶意请求）
- 多Agent协作工作流（单例模式，避免重复初始化）
"""
import threading
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
from utils.auth_service import AuthService
from utils.chat_session_service import ChatSessionService
from rag.vector_store import VectorStoreService
from utils.logger_handler import logger
from utils.langsmith_tracker import log_langsmith_status
from utils.db_pool import get_db_session
import os
import shutil
import time
from datetime import datetime
import json

# 应用启动时打印追踪状态（LangSmith + TokenTracker）
log_langsmith_status()

app = FastAPI(
    title="AI智能客服API",
    description="提供聊天、会话管理、知识库管理等功能的REST API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局异常处理中间件 (#7) ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回统一格式的错误响应，避免泄露内部信息"""
    logger.error(f"[全局异常] {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "服务器内部错误", "detail": str(exc)}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一HTTP异常响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail}
    )

# ==================== API速率限制 (#9) ====================
# 使用简单的内存字典实现速率限制，每用户每分钟最多60次请求
_rate_limit_store = {}  # {user_id: [timestamp1, timestamp2, ...]}
RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）
RATE_LIMIT_MAX = 60     # 窗口内最大请求数


def check_rate_limit(user_id):
    """
    检查用户是否超过速率限制

    Args:
        user_id: 用户唯一标识

    Returns:
        bool: True表示未超限，False表示已超限
    """
    now = time.time()
    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []
    # 清理过期的记录
    _rate_limit_store[user_id] = [
        t for t in _rate_limit_store[user_id] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[user_id].append(now)
    return True


security = HTTPBearer()

auth_service = AuthService()
chat_service = ChatSessionService()
vector_service = VectorStoreService()

# ==================== 多Agent工作流单例 (#1) ====================
# 在应用启动时创建一次，所有请求共享同一实例，避免每次重建4个Agent
_workflow_instance = None
_workflow_lock = threading.Lock()


def get_workflow():
    """
    获取MultiAgentWorkflow单例实例

    采用懒加载模式：首次调用时创建，后续复用。
    这样所有聊天请求共享同一个Supervisor和3个Specialist Agent，
    避免每次请求都重新初始化LLM模型连接。
    """
    global _workflow_instance
    if _workflow_instance is None:
        with _workflow_lock:
            if _workflow_instance is None:
                from agent.workflow import MultiAgentWorkflow
                _workflow_instance = MultiAgentWorkflow()
                logger.info("[API] MultiAgentWorkflow单例创建完成")
    return _workflow_instance

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    user_info = auth_service.verify_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的token或token已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_info

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    # 消息内容，限制1-2000字符，防止超长消息导致Token溢出 (#6)
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息内容，1-2000字符")

class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str

@app.post("/api/auth/register", summary="用户注册")
async def register(request: RegisterRequest):
    result = auth_service.register(request.username, request.email, request.password)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result

@app.post("/api/auth/login", summary="用户登录")
async def login(request: LoginRequest):
    result = auth_service.login(request.username, request.password)
    if not result['success']:
        raise HTTPException(status_code=401, detail=result['message'])
    return result

@app.get("/api/auth/me", summary="获取当前用户信息", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    user = auth_service.get_user_by_id(current_user['user_id'])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

def get_or_create_session(session_id: Optional[str]) -> str:
    """
    获取或创建会话ID
    新逻辑：消息归入当前会话，不自动新建
    - 如果传入了session_id且存在，使用它
    - 如果没有传入session_id，获取最新会话
    - 只有没有任何会话时才创建新会话
    """
    if session_id and chat_service.session_exists(session_id):
        return session_id
    latest = chat_service.get_latest_session()
    if latest:
        return latest['session_id']
    return chat_service.create_session()


@app.post("/api/chat", summary="发送聊天消息")
async def chat(request: ChatRequest, current_user: Dict = Depends(get_current_user)):
    # 速率限制检查 (#9)
    if not check_rate_limit(current_user['user_id']):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    try:
        session_id = get_or_create_session(request.session_id)

        user_save_result = chat_service.save_message(session_id, "user", request.message)
        if not user_save_result:
            logger.error(f"[流式输出] 保存用户消息失败，session_id: {session_id}")

        # 使用单例工作流 (#1)
        workflow = get_workflow()

        full_response = ""
        for chunk in workflow.execute_stream(request.message):
            full_response += chunk

        chat_service.save_message(session_id, "assistant", full_response)

        return {
            'session_id': session_id,
            'message': {
                'role': 'assistant',
                'content': full_response
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天接口错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误")

@app.post("/api/chat/stream", summary="流式发送聊天消息")
async def chat_stream(request: ChatRequest, current_user: Dict = Depends(get_current_user)):
    # 速率限制检查 (#9)
    if not check_rate_limit(current_user['user_id']):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    session_id = get_or_create_session(request.session_id)

    chat_service.save_message(session_id, "user", request.message)

    # 使用单例工作流 (#1)
    workflow = get_workflow()
    
    async def generate():
        full_response = ""
        try:
            for chunk in workflow.execute_stream(request.message):
                for char in chunk:
                    full_response += char
                    yield json.dumps({
                        'type': 'chunk',
                        'content': char
                    }) + '\n'
        except Exception as e:
            logger.error(f"流式输出错误: {str(e)}")
            yield json.dumps({
                'type': 'error',
                'error': str(e)
            }) + '\n'
            return
        
        save_result = chat_service.save_message(session_id, "assistant", full_response)
        if not save_result:
            logger.error(f"[流式输出] 保存助手消息失败，session_id: {session_id}")
        
        yield json.dumps({
            'type': 'end',
            'session_id': session_id,
            'full_content': full_response
        }) + '\n'
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/api/sessions", summary="创建新会话")
async def create_session(current_user: Dict = Depends(get_current_user)):
    """显式创建新会话，用户点击"新建对话"时调用"""
    session_id = chat_service.create_session()
    if not session_id:
        raise HTTPException(status_code=500, detail="创建会话失败")
    return {'session_id': session_id, 'message': '会话创建成功'}

@app.get("/api/sessions/latest", summary="获取最新会话")
async def get_latest_session(current_user: Dict = Depends(get_current_user)):
    """获取用户最近一次会话，如果不存在则自动创建"""
    latest = chat_service.get_latest_session()
    if not latest:
        session_id = chat_service.create_session()
        return {'session_id': session_id, 'messages': []}
    return {'session_id': latest['session_id']}

@app.get("/api/sessions", summary="获取用户会话列表", response_model=List[SessionResponse])
async def get_sessions(current_user: Dict = Depends(get_current_user)):
    sessions = chat_service.get_all_sessions()
    
    result = []
    for session in sessions:
        session_dict = session.copy()
        if isinstance(session_dict.get('created_at'), datetime):
            session_dict['created_at'] = session_dict['created_at'].isoformat()
        if isinstance(session_dict.get('updated_at'), datetime):
            session_dict['updated_at'] = session_dict['updated_at'].isoformat()
        
        messages = chat_service.get_session_messages(session['session_id'])
        if messages and len(messages) > 0:
            first_message = messages[0]['content']
            session_dict['title'] = first_message[:20] + ('...' if len(first_message) > 20 else '')
        else:
            session_dict['title'] = '新对话'
        result.append(session_dict)
    
    return result

@app.get("/api/sessions/{session_id}/messages", summary="获取会话消息", response_model=List[MessageResponse])
async def get_session_messages(session_id: str, current_user: Dict = Depends(get_current_user)):
    if not chat_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = chat_service.get_session_messages(session_id)
    return messages

@app.delete("/api/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str, current_user: Dict = Depends(get_current_user)):
    if not chat_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    success = chat_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除会话失败")
    return {'success': True, 'message': '会话删除成功'}

@app.post("/api/knowledge/reload", summary="重新加载知识库")
async def reload_knowledge(current_user: Dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作")
    
    vector_service.load_documents()
    return {'success': True, 'message': '知识库重新加载成功'}

@app.get("/api/knowledge/files", summary="获取知识库文件列表")
async def get_knowledge_files(current_user: Dict = Depends(get_current_user)):
    from utils.config_handler import chroma_conf
    data_path = chroma_conf.get('data_path', 'data')
    from utils.file_handler import listdir_with_allowed_type
    
    files = listdir_with_allowed_type(data_path)
    return {'files': files}

@app.delete("/api/knowledge/files/{filename}", summary="删除知识库文件")
async def delete_knowledge_file(filename: str, current_user: Dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作")
    
    from utils.config_handler import chroma_conf
    data_path = chroma_conf.get('data_path', 'data')
    file_path = os.path.join(data_path, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    os.remove(file_path)
    
    md5_file = chroma_conf.get('md5_hex_store', 'md5.text')
    if os.path.exists(md5_file):
        with open(md5_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(md5_file, 'w', encoding='utf-8') as f:
            for line in lines:
                if filename not in line:
                    f.write(line)
    
    return {'success': True, 'message': '文件删除成功'}

@app.post("/api/knowledge/upload", summary="上传知识库文件")
async def upload_knowledge_file(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作")
    
    from utils.config_handler import chroma_conf
    data_path = chroma_conf.get('data_path', 'data')
    
    allowed_extensions = ['.txt', '.pdf', '.csv']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")
    
    file_path = os.path.join(data_path, file.filename)
    
    with open(file_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    return {'success': True, 'message': '文件上传成功', 'filename': file.filename}

@app.get("/", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "AI智能客服API"}

# 注册Token统计路由
from api.stats import router as stats_router
app.include_router(stats_router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
