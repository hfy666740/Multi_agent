"""
Token统计API路由
提供Token消耗统计和历史记录的查询接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional
from utils.token_stats_service import get_token_stats_service
from utils.logger_handler import logger

# 创建路由，prefix="/api/stats", tags=["stats"]
router = APIRouter(prefix="/api/stats", tags=["Token统计"])


# 从 api/main.py 复用 get_current_user 依赖
# 注意：这里需要从 api.main 导入，避免循环依赖
from api.main import get_current_user


@router.get("/tokens", summary="获取Token消耗统计")
async def get_token_stats(
    session_id: Optional[str] = Query(None, description="按会话ID筛选"),
    current_user: Dict = Depends(get_current_user)
):
    """
    获取Token消耗统计汇总
    
    返回各来源（supervisor/knowledge/weather/report/direct）的
    Token消耗统计，以及总计。
    
    - 管理员可查看所有用户的统计
    - 普通用户仅查看自己的统计
    """
    try:
        service = get_token_stats_service()
        stats = service.get_stats(session_id=session_id)
        return {"code": 200, "data": stats}
    except Exception as e:
        logger.error(f"[TokenStats API] 查询统计失败: {e}")
        raise HTTPException(status_code=500, detail="查询Token统计失败")


@router.get("/tokens/history", summary="获取Token消耗历史")
async def get_token_history(
    limit: int = Query(50, ge=1, le=200, description="返回记录数，1-200"),
    session_id: Optional[str] = Query(None, description="按会话ID筛选"),
    current_user: Dict = Depends(get_current_user)
):
    """
    获取Token消耗历史记录列表
    
    按时间倒序返回最近的Token消耗记录。
    每次LLM调用产生一条记录，包含来源、输入/输出Token数、关联会话等。
    """
    try:
        service = get_token_stats_service()
        history = service.get_history(limit=limit, session_id=session_id)
        return {"code": 200, "data": history}
    except Exception as e:
        logger.error(f"[TokenStats API] 查询历史失败: {e}")
        raise HTTPException(status_code=500, detail="查询Token历史失败")