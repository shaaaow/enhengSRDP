"""预留路由 — 自定义解算，待算法就绪后接入"""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["预留功能"])


@router.post("/api/localization/custom")
async def custom_localization():
    raise HTTPException(
        status_code=501,
        detail="自定义解算功能开发中，请将算法文件放入 backend/algorithms/ 后启用",
    )
