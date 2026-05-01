"""预留路由 — 语音识别与自定义解算，待算法就绪后接入"""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["预留功能"])


@router.post("/api/speech/recognize")
async def recognize_speech():
    raise HTTPException(
        status_code=501,
        detail="语音识别功能开发中，请将算法文件放入 backend/algorithms/ 后启用",
    )


@router.post("/api/localization/custom")
async def custom_localization():
    raise HTTPException(
        status_code=501,
        detail="自定义解算功能开发中，请将算法文件放入 backend/algorithms/ 后启用",
    )
